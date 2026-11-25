"""Contract 0.2 test against the fake World (-run=AarsFakeWorld): plays the Simulator side with every valid
example, checks the World's reaction, sends contract-breaking messages, and validates every message the World
sends against messages.schema.json."""
import glob
import json
import os
import time

import mini_schema
import ws_client


class Session:
    def __init__(self, port):
        self.c = ws_client.WsClient("127.0.0.1", port)

    def frames(self):
        return ws_client.decode(list(self.c.frames))

    def mark(self):
        return len(self.c.frames)

    def send(self, obj):
        if isinstance(obj, (dict, list)):
            self.c.send_json(obj)
        else:
            self.c.send_frame(obj)

    def wait(self, pred, after=0, timeout=1.5):
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < timeout:
            for _, _, o, _ in self.frames()[after:]:
                if o is not None and pred(o):
                    return o
            time.sleep(0.02)
        return None

    def state(self, pred, after, timeout=1.5):
        return self.wait(lambda o: o.get("type") == "world.state" and pred(o), after, timeout)

    def close(self):
        self.c.close()


def rx(st, rid):
    return next((r for r in st["receivers"] if r["id"] == rid), None)


def run_contract(port, contract_dir):
    schema = mini_schema.load(os.path.join(contract_dir, "schema", "messages.schema.json"))
    ex = {os.path.basename(f)[:-5]: json.load(open(f, encoding="utf-8"))
          for f in glob.glob(os.path.join(contract_dir, "examples", "valid", "*.json"))}
    checks = []

    def check(name, ok, detail=""):
        checks.append({"check": name, "ok": bool(ok), "detail": detail if not ok else ""})

    s = Session(port)
    first = s.wait(lambda o: True, 0, 2.0)
    check("World sends hello first", first and first.get("type") == "hello" and first.get("role") == "world" and first.get("version") == "0.2", first)
    s.send(ex["hello.sim"])

    m = s.mark(); s.send(ex["ping"])
    p = s.wait(lambda o: o.get("type") == "pong", m)
    check("ping -> pong with same id and t_ms", p and p["id"] == "p-101" and p["t_ms"] == 606800, p)

    m = s.mark(); s.send(ex["clock.set"])
    check("clock.set scale 4 -> world.state.clock.scale 4", s.state(lambda o: o["clock"]["scale"] == 4, m))
    m = s.mark(); s.send({"type": "clock.set", "scale": 1, "paused": True})
    st = s.state(lambda o: o["clock"]["paused"], m)
    st2 = s.state(lambda o: o["clock"]["paused"] and st and o["seq"] > st["seq"] + 3, m)
    check("clock.set paused -> t_ms frozen", st and st2 and st["t_ms"] == st2["t_ms"], (st and st["t_ms"], st2 and st2["t_ms"]))
    s.send({"type": "clock.set", "scale": 1, "paused": False})

    m = s.mark(); s.send(ex["pod.hose"])
    check("pod.hose LEFT 31.5 -> pods.LEFT.tip_ft 31.5", s.state(lambda o: o["pods"]["LEFT"]["tip_ft"] == 31.5 and o["pods"]["RIGHT"]["tip_ft"] == 0, m))
    m = s.mark(); s.send(dict(ex["pod.hose"], seq=36400, payout_ft=50))
    check("stale pod.hose (lower seq) ignored", s.state(lambda o: o["pods"]["LEFT"]["tip_ft"] == 50, m, 0.5) is None)

    for k in ("pod.fluid", "boom.fluid", "camera.lens"):
        s.send(ex[k])

    m = s.mark(); s.send(ex["boom.drive"])
    check("boom.drive -> boom.tip", s.state(lambda o: o["boom"]["tip"] == {"az_deg": 2.1, "el_deg": 30.4, "tele_ft": 11.8}, m))

    m = s.mark(); s.send(ex["tanker.set"])
    a = s.state(lambda o: o["tanker"]["bank_deg"] == 15 and o["tanker"]["ap"] == "OFF", m)
    b = s.state(lambda o: a and o["seq"] > a["seq"] + 30, m)
    check("tanker.set bank 15 / ap OFF", a, a and a["tanker"])
    check("tanker turns while banked", a and b and b["tanker"]["heading_deg"] != a["tanker"]["heading_deg"])
    s.send({"type": "tanker.set", "bank_deg": 0, "ias_kt": 260})

    m = s.mark(); s.send(ex["receiver.add"])
    check("receiver.add TIGER1 -> receivers[]", s.state(lambda o: (rx(o, "TIGER1") or {}).get("behind") == "LEFT" and rx(o, "TIGER1")["type"] == "RAFALE", m))
    m = s.mark(); s.send(ex["receiver.command"])
    check("receiver.command ASTERN -> phase ASTERN", s.state(lambda o: (rx(o, "TIGER1") or {}).get("phase") == "ASTERN", m))
    m = s.mark(); s.send({"type": "receiver.command", "id": "TIGER1", "action": "CONTACT"})
    check("CONTACT -> pods.LEFT contact, receiver_id, drogue pushed 6 ft",
          s.state(lambda o: o["pods"]["LEFT"] == {"tip_ft": 25.5, "contact": True, "receiver_id": "TIGER1"}, m))
    m = s.mark(); s.send(ex["pod.hose.attached"])
    check("pod.hose attached 74 -> tip 68 in contact", s.state(lambda o: o["pods"]["LEFT"]["tip_ft"] == 68 and o["pods"]["LEFT"]["contact"], m))

    m = s.mark(); s.send({"type": "receiver.add", "id": "LANCE1", "receiver_type": "F-35", "behind": "BOOM"})
    s.send({"type": "receiver.command", "id": "LANCE1", "action": "ASTERN"})
    st = s.state(lambda o: o["boom"]["hole"] is not None, m)
    check("boom receiver ASTERN -> hole + track_box + receiver_id", st and st["boom"]["track_box"] is not None and st["boom"]["receiver_id"] == "LANCE1", st and st["boom"])
    m = s.mark(); s.send({"type": "receiver.command", "id": "LANCE1", "action": "CONTACT"}); s.send(ex["boom.drive.attached"])
    st = s.state(lambda o: o["boom"]["contact"] and o["boom"]["tip"]["tele_ft"] == o["boom"]["hole"]["range_ft"], m)
    check("boom CONTACT + attached -> tip follows the hole", st, st and st["boom"])

    m = s.mark(); s.send(ex["receiver.remove"])
    check("receiver.remove TIGER1 -> gone, LEFT contact false", s.state(lambda o: rx(o, "TIGER1") is None and not o["pods"]["LEFT"]["contact"], m))

    m = s.mark(); s.send(ex["pod.hose.cut"])
    check("pod.hose cut RIGHT -> tip 0", s.state(lambda o: o["pods"]["RIGHT"]["tip_ft"] == 0, m))

    m = s.mark(); s.send(ex["snapshot.request"])
    rep = s.wait(lambda o: o.get("type") == "snapshot.reply", m)
    check("snapshot.request -> snapshot.reply with restore", rep and rep["request_id"] == "snap-7" and isinstance(rep.get("restore"), dict) and rep["restore"].get("format"), rep)
    if rep:
        m = s.mark(); s.send({"type": "world.set", "t_ms": 1234, "restore": rep["restore"]})
        a = s.state(lambda o: o["t_ms"] == 1234, m)
        b = s.state(lambda o: a and o["seq"] > a["seq"] + 5, m)
        check("world.set -> World shows t_ms 1234 and holds it", a and b and b["t_ms"] == 1234, (a and a["t_ms"], b and b["t_ms"]))
        check("world.set -> restored receivers (LANCE1)", a and rx(a, "LANCE1") is not None)
        m = s.mark(); s.send(ex["world.resume"])
        check("world.resume -> time runs from 1234", s.state(lambda o: o["t_ms"] > 1300, m))

    # contract-breaking messages: each must be rejected and change nothing
    bad = [
        dict(ex["pod.hose"], seq=40000, payout_ft=99, extra=1),          # unknown field
        {"type": "camera.lens", "pod": "MIDDLE", "lens": "WIDE"},       # bad enum
        {"type": "boom.drive", "seq": 90000, "t_ms": 1, "el_deg": 1, "az_deg": 1, "attached": False},  # missing tele_ft
        {"type": "clock.set", "scale": 0, "paused": False},             # exclusiveMinimum 0
        {"type": "clock.set", "scale": 101, "paused": False},           # maximum 100
        dict(ex["pod.hose"], seq=40001, payout_ft="31"),                # wrong type
        dict(ex["pod.hose"], seq=40002.5),                              # non-integer seq
        {"type": "tanker.set"},                                         # minProperties 2
        {"type": "receiver.remove", "id": "X" * 33},                    # id too long
        {"type": "foo"},                                                # unknown type
        {"type": "pong", "id": "a", "t_ms": 1},                         # World-only message
        "not json",                                                     # not JSON
        {"type": "hello", "role": "sim", "name": "x", "version": "1.0"},  # bad version format
        {"type": "receiver.add", "id": "N", "receiver_type": "F-16", "behind": None},  # behind null
    ]
    m = s.mark()
    for b in bad:
        s.send(b)
    st = s.state(lambda o: True, m)
    time.sleep(0.3)
    st = s.state(lambda o: True, s.mark()) or st
    check("rejected messages changed nothing", st and st["pods"]["LEFT"]["tip_ft"] == 74 and st["clock"]["scale"] == 1 and rx(st, "N") is None,
          st and (st["pods"]["LEFT"], st["clock"]))

    # second connection with another contract version: ignored until a matching hello
    s2 = Session(port)
    s2.wait(lambda o: o.get("type") == "hello", 0, 2.0)
    s2.send({"type": "hello", "role": "sim", "name": "old-sim", "version": "0.3"})
    m = s2.mark(); s2.send({"type": "ping", "id": "v-1", "t_ms": 1})
    check("version 0.3 -> ignored (no pong)", s2.wait(lambda o: o.get("type") == "pong", m, 0.6) is None)
    s2.send(ex["hello.sim"])
    m = s2.mark(); s2.send({"type": "ping", "id": "v-2", "t_ms": 2})
    check("matching hello -> answered again", s2.wait(lambda o: o.get("type") == "pong" and o["id"] == "v-2", m))
    n0 = s.mark()
    time.sleep(0.3)
    check("new connection replaces the old one (old gets no more world.state)",
          not any(o and o.get("type") == "world.state" for _, _, o, _ in s.frames()[n0:]))

    # every World message against the schema
    allmsgs = [(o, raw) for sess in (s, s2) for _, op, o, raw in sess.frames() if op in (1, 2)]
    errors = []
    for o, raw in allmsgs:
        e = ["not JSON: %r" % raw[:60]] if o is None else schema.errors(o)
        if e:
            errors.append({"msg": (o or {}).get("type"), "errors": e[:3]})
    types = {}
    for o, _ in allmsgs:
        if o:
            types[o.get("type")] = types.get(o.get("type"), 0) + 1
    states = [o for o, _ in allmsgs if o and o.get("type") == "world.state"]
    check("every World message matches the schema", not errors, errors[:5])
    check("restore carried in ~half of world.state (-restore)", states and 0.4 < sum(1 for o in states if "restore" in o) / len(states) < 0.6)
    check("all frames binary with plain JSON", all(op == 2 for sess in (s, s2) for _, op, _, _ in sess.frames()))

    s2.send({"type": "quit"})
    time.sleep(0.5)
    s.close(); s2.close()
    return {"checks": checks, "passed": sum(c["ok"] for c in checks), "total": len(checks),
            "world_messages": types, "schema_errors": errors[:20], "bad_sent": len(bad)}


def run_fixes(port, contract_dir):
    """World fed with out-of-contract values (-badvalues): every world.state must still match the schema."""
    schema = mini_schema.load(os.path.join(contract_dir, "schema", "messages.schema.json"))
    s = Session(port)
    s.send({"type": "hello", "role": "sim", "name": "fixes-test", "version": "0.2"})
    time.sleep(1.0)
    states = [o for _, _, o, _ in s.frames() if o and o.get("type") == "world.state"]
    errors = [schema.errors(o)[:3] for o in states if schema.errors(o)]
    last = states[-1] if states else {}
    s.send({"type": "quit"})
    time.sleep(0.3)
    s.close()
    checks = [
        {"check": "every world.state matches the schema", "ok": bool(states) and not errors, "detail": errors[:3]},
        {"check": "heading wrapped to [0,360)", "ok": 0 <= last.get("tanker", {}).get("heading_deg", -1) < 360, "detail": last.get("tanker")},
        {"check": "bank/pitch clamped, ias >= 0, NaN alt -> 0", "ok": last.get("tanker", {}).get("bank_deg") == 90 and last["tanker"]["pitch_deg"] == -90
            and last["tanker"]["ias_kt"] == 0 and last["tanker"]["alt_ft"] == 0, "detail": last.get("tanker")},
        {"check": "empty-id receiver skipped, bad restore omitted", "ok": "restore" not in last and all(r["id"] for r in last.get("receivers", [])), "detail": ""},
        {"check": "long receiver_id cut to 32", "ok": len(last.get("pods", {}).get("RIGHT", {}).get("receiver_id") or "") == 32, "detail": last.get("pods")},
    ]
    return {"checks": checks, "passed": sum(c["ok"] for c in checks), "total": len(checks), "states": len(states)}
