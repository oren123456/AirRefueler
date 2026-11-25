"""Drives the AirRefueler hose through the AARS link like the Simulator's drum would, and checks world.state.
Usage: <Unreal python.exe> hose_check.py [port] [pod]"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import contract_test  # noqa: E402

port = int(sys.argv[1]) if len(sys.argv) > 1 else 9100
pod = sys.argv[2] if len(sys.argv) > 2 else "LEFT"
s = contract_test.Session(port)
s.wait(lambda o: o.get("type") == "hello", 0, 3.0)
s.send({"type": "hello", "role": "sim", "name": "hose-check", "version": "0.2"})
seq = [0]
log = []
checks = []


def tip():
    st = s.state(lambda o: True, s.mark(), 1.0)
    return st["pods"][pod]["tip_ft"] if st else None


def drum(start, end, rate_fps, attached=False, cut=False):
    """Pay out / reel in from start to end ft at rate ft/s, 60 Hz, then hold 1.5 s."""
    t0 = time.perf_counter()
    dur = abs(end - start) / rate_fps if rate_fps else 0
    while True:
        t = time.perf_counter() - t0
        p = end if t >= dur else start + (end - start) * t / dur
        seq[0] += 1
        s.send({"type": "pod.hose", "seq": seq[0], "t_ms": int(t * 1000), "pod": pod, "payout_ft": round(p, 3), "attached": attached, "cut": cut})
        if t >= dur + 1.5:
            break
        time.sleep(1 / 60)
    return tip()


def check(name, ok, detail):
    checks.append({"check": name, "ok": bool(ok), "detail": detail})


t = drum(78.74, 78.74, 0)
check("hold 78.7 ft -> tip ~78.7", t is not None and abs(t - 78.74) < 3, t)
t = drum(78.74, 0, 15)
check("reel in to 0 -> tip 0 (stowed)", t is not None and t < 1, t)
t = drum(0, 50, 15)
check("pay out to 50 ft -> tip ~50", t is not None and abs(t - 50) < 3, t)
t = drum(50, 90, 15)
check("pay out to 90 ft (past the old 24 m stop) -> tip ~90", t is not None and abs(t - 90) < 3, t)
t = drum(90, 70, 15)
check("reel in to 70 ft -> tip ~70", t is not None and abs(t - 70) < 3, t)
states = [o for _, _, o, _ in s.frames() if o and o.get("type") == "world.state"]
rate = len(states) / max(1e-6, s.frames()[-1][0] - s.frames()[0][0])
check("world.state rate ~60 Hz (editor in background)", 50 < rate < 70, round(rate, 1))
s.close()
out = {"checks": checks, "passed": sum(c["ok"] for c in checks), "total": len(checks)}
json.dump(out, open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Results", "hose_check.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
