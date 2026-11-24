"""Minimal raw-socket WebSocket client (stdlib only) for testing the Unreal WebSocketNetworking server.
Records every frame exactly as it arrives (opcode, bytes) so framing can be checked."""
import base64, hashlib, json, os, socket, struct, threading, time


def stats(v):
    if not v:
        return {"n": 0}
    s = sorted(v)
    return {"n": len(s), "mean": sum(s) / len(s), "p50": s[len(s) // 2],
            "p99": s[min(len(s) - 1, int(len(s) * 0.99))], "max": s[-1], "min": s[0]}


class WsClient:
    def __init__(self, host, port, subprotocol=None, nodelay=True):
        self.sock = socket.create_connection((host, port), timeout=10)
        if nodelay:
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        key = base64.b64encode(os.urandom(16)).decode()
        req = ("GET / HTTP/1.1\r\nHost: %s:%d\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
               "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n" % (host, port, key))
        if subprotocol:
            req += "Sec-WebSocket-Protocol: %s\r\n" % subprotocol
        self.sock.sendall((req + "\r\n").encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("closed during handshake: %r" % buf)
            buf += chunk
        head, self.pending = buf.split(b"\r\n\r\n", 1)
        self.handshake = head.decode(errors="replace")
        if " 101 " not in self.handshake.split("\r\n")[0]:
            raise ConnectionError("handshake refused: " + self.handshake)
        accept = base64.b64encode(hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()).decode()
        self.accept_ok = accept in self.handshake
        self.sock.settimeout(None)
        self.frames = []          # (t, opcode, fin, payload)
        self.recv_sizes = []      # bytes per recv() call
        self.closed = False
        self.lock = threading.Lock()
        self.t = threading.Thread(target=self._reader, daemon=True)
        self.t.start()

    def _read(self, n):
        while len(self.pending) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("closed")
            self.recv_sizes.append(len(chunk))
            self.pending += chunk
        out, self.pending = self.pending[:n], self.pending[n:]
        return out

    def _reader(self):
        try:
            while True:
                b0, b1 = self._read(2)
                fin, op = b0 >> 7, b0 & 0x0F
                n = b1 & 0x7F
                if n == 126:
                    n = struct.unpack(">H", self._read(2))[0]
                elif n == 127:
                    n = struct.unpack(">Q", self._read(8))[0]
                if b1 & 0x80:
                    self._read(4)
                payload = self._read(n)
                now = time.perf_counter()
                with self.lock:
                    self.frames.append((now, op, fin, payload))
                if op == 8:
                    break
        except Exception:
            pass
        self.closed = True

    def send_frame(self, payload, opcode=1, fin=True):
        if isinstance(payload, str):
            payload = payload.encode()
        hdr = bytes([(0x80 if fin else 0) | opcode])
        n = len(payload)
        if n < 126:
            hdr += bytes([0x80 | n])
        elif n < 65536:
            hdr += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            hdr += bytes([0x80 | 127]) + struct.pack(">Q", n)
        mask = os.urandom(4)
        body = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self.sock.sendall(hdr + mask + body)

    def send_json(self, obj, opcode=1):
        self.send_frame(json.dumps(obj, separators=(",", ":")), opcode)

    def close(self):
        try:
            self.send_frame(struct.pack(">H", 1000), opcode=8)
            time.sleep(0.2)
        except Exception:
            pass
        try:
            self.sock.close()
        except Exception:
            pass


def decode(frames):
    """Return list of (t, opcode, obj or None, raw)."""
    out = []
    for t, op, fin, p in frames:
        obj = None
        try:
            obj = json.loads(p.decode("utf-8"))
        except Exception:
            pass
        out.append((t, op, obj, p))
    return out


def run_stream(port, seconds, ping_hz=10, pod_hz=60):
    """Simulator-like load: pod.hose at 60 Hz, ping at 10 Hz. Measures world.state arrivals and ping RTT."""
    c = WsClient("127.0.0.1", port)
    c.send_json({"type": "hello", "role": "sim", "name": "aars-sim-test", "version": "0.2"})
    t0 = time.perf_counter()
    ping_sent = {}
    seq = 0
    next_pod = t0
    next_ping = t0
    k = 0
    while time.perf_counter() - t0 < seconds and not c.closed:
        now = time.perf_counter()
        if now >= next_pod:
            c.send_json({"type": "pod.hose", "seq": seq, "t_ms": int((now - t0) * 1000), "pod": "LEFT",
                         "payout_ft": 31.5, "attached": False, "cut": False})
            seq += 1
            next_pod += 1.0 / pod_hz
        if now >= next_ping:
            pid = "p-%d" % k
            k += 1
            ping_sent[pid] = time.perf_counter()
            c.send_json({"type": "ping", "id": pid, "t_ms": int((now - t0) * 1000)})
            next_ping += 1.0 / ping_hz
        time.sleep(0.0005)
    time.sleep(0.5)
    c.send_json({"type": "quit"})
    time.sleep(0.5)
    c.close()
    fr = decode(c.frames)
    ops = {}
    for _, op, _, _ in fr:
        ops[op] = ops.get(op, 0) + 1
    states = [(t, o) for t, op, o, _ in fr if o and o.get("type") == "world.state"]
    gaps = [(states[i][0] - states[i - 1][0]) * 1000 for i in range(1, len(states))]
    seqs = [o["seq"] for _, o in states]
    seq_gaps = sum(1 for i in range(1, len(seqs)) if seqs[i] != seqs[i - 1] + 1)
    rtts = []
    late = []
    for t, op, o, _ in fr:
        if o and o.get("type") == "pong" and o.get("id") in ping_sent:
            rtts.append((t - ping_sent[o["id"]]) * 1000)
    # RTT trend: first vs last quarter (backlog growth shows as rising RTT)
    q = max(1, len(rtts) // 4)
    first_payloads = [p[:12].hex(" ") for _, _, _, p in fr[:3]]
    return {
        "handshake_status": c.handshake.split("\r\n")[0], "handshake": c.handshake, "accept_ok": c.accept_ok,
        "opcodes": ops, "first_payload_hex": first_payloads,
        "starts_with_brace": all(p[:1] == b"{" for _, _, _, p in fr if p),
        "unparsed_frames": sum(1 for _, op, o, _ in fr if o is None and op in (1, 2)),
        "world_state_rx": len(states), "world_state_seq_gaps": seq_gaps,
        "world_state_interarrival_ms": stats(gaps),
        "pings_sent": len(ping_sent), "pongs_rx": len(rtts), "rtt_ms": stats(rtts),
        "rtt_first_quarter_mean": sum(rtts[:q]) / q if rtts else None,
        "rtt_last_quarter_mean": sum(rtts[-q:]) / q if rtts else None,
        "recv_calls": len(c.recv_sizes), "frames_rx": len(fr),
    }


def run_quiet_burst(port, seconds):
    """Client sends nothing after hello, so it does not piggy-back ACKs. The server sends A,B pairs.
    With Nagle on, B waits for the (delayed) ACK of A -> gap of tens to ~200 ms."""
    c = WsClient("127.0.0.1", port)
    c.send_json({"type": "hello", "role": "sim", "name": "aars-sim-test", "version": "0.2"})
    time.sleep(seconds)
    c.send_json({"type": "quit"})
    time.sleep(0.5)
    c.close()
    fr = decode(c.frames)
    a = {}
    gaps = []
    for t, op, o, _ in fr:
        if o and o.get("type") == "burst":
            if o["part"] == "A":
                a[o["n"]] = t
            elif o["n"] in a:
                gaps.append((t - a[o["n"]]) * 1000)
    return {"pairs": len(gaps), "a_to_b_gap_ms": stats(gaps)}


def run_framing(port):
    """Frame-type and connection-handling checks."""
    res = {}
    c = WsClient("127.0.0.1", port)
    res["no_subprotocol_handshake"] = c.handshake
    c.send_json({"type": "hello", "role": "sim", "name": "text-frame", "version": "0.2"})                 # text
    raw = json.dumps({"type": "hello", "role": "sim", "name": "binary-raw", "version": "0.2"}).encode()
    c.send_frame(raw, opcode=2)                                                                        # binary, no prefix
    c.send_frame(struct.pack("<I", len(raw)) + raw.replace(b"binary-raw", b"binary-pfx"), opcode=2)   # binary + 4-byte LE size
    frag = json.dumps({"type": "hello", "role": "sim", "name": "fragmented", "version": "0.2"}).encode()
    c.send_frame(frag[:10], opcode=1, fin=False)                                                       # text, 2 fragments
    c.send_frame(frag[10:], opcode=0, fin=True)
    big = {"type": "echo", "pad": "x" * 200000}
    c.send_json(big)                                                                                   # 200 KB echo
    time.sleep(1.0)
    fr = decode(c.frames)
    echo = [x for x in fr if x[2] and x[2].get("type") == "echo"]
    res["echo_200k_ok"] = bool(echo) and len(echo[0][3]) == len(json.dumps(big, separators=(",", ":")))
    res["echo_opcode"] = echo[0][1] if echo else None
    # second concurrent client
    try:
        c2 = WsClient("127.0.0.1", port)
        res["second_client_accepted"] = True
        c2.send_json({"type": "hello", "role": "sim", "name": "second-client", "version": "0.2"})
        time.sleep(0.3)
        c2.close()
    except Exception as e:
        res["second_client_accepted"] = "error: %s" % e
    c.close()
    time.sleep(0.5)
    # subprotocol handling, then a plain reconnect with ping/pong
    for label, sp in (("subprotocol_aars", "aars"), ("subprotocol_binary", "binary")):
        try:
            cx = WsClient("127.0.0.1", port, subprotocol=sp)
            res[label] = cx.handshake.split("\r\n")[0] + (" | " + [l for l in cx.handshake.split("\r\n") if "Protocol" in l][0] if "Protocol" in cx.handshake else "")
            cx.close()
        except Exception as e:
            res[label] = "error: %s" % e
        time.sleep(0.3)
    try:
        c3 = WsClient("127.0.0.1", port)
        c3.send_json({"type": "ping", "id": "rc-1", "t_ms": 1})
        time.sleep(0.5)
        fr3 = decode(c3.frames)
        res["reconnect_pong"] = any(o and o.get("type") == "pong" for _, _, o, _ in fr3)
        res["reconnect_world_state"] = sum(1 for _, _, o, _ in fr3 if o and o.get("type") == "world.state")
        c3.send_json({"type": "quit"})
        time.sleep(0.3)
        c3.close()
    except Exception as e:
        res["reconnect_pong"] = "error: %s" % e
    return res
