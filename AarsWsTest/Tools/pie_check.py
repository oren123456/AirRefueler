"""Checks the AARS link of the running AirRefueler game (PIE): connect, read world.state, send a few Simulator
messages, validate everything Unreal sends. Usage: <Unreal python.exe> pie_check.py [port] [contract_dir]"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import contract_test  # noqa: E402
import mini_schema  # noqa: E402

port = int(sys.argv[1]) if len(sys.argv) > 1 else 9100
contract = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                                               "AARS-world-contract-0.2", "AARS-world-contract-0.2")
schema = mini_schema.load(os.path.join(contract, "schema", "messages.schema.json"))
checks = []


def check(name, ok, detail=""):
    checks.append({"check": name, "ok": bool(ok), "detail": "" if ok else detail})


s = contract_test.Session(port)
hello = s.wait(lambda o: True, 0, 2.0)
check("hello from AirRefueler", hello and hello.get("type") == "hello" and hello.get("role") == "world", hello)
s.send({"type": "hello", "role": "sim", "name": "pie-check", "version": "0.2"})
st = s.state(lambda o: True, 0, 2.0)
check("world.state arrives", st, st)
if st:
    check("the trailed hose is reported (~24 m = ~79 ft on one pod)", any(70 < p["tip_ft"] < 85 for p in st["pods"].values()), st["pods"])
    check("player Mirage reported as receiver PLAYER", any(r["id"] == "PLAYER" for r in st["receivers"]), st["receivers"])
m = s.mark(); s.send({"type": "ping", "id": "pie-1", "t_ms": 7})
p = s.wait(lambda o: o.get("type") == "pong", m)
check("ping -> pong", p and p["id"] == "pie-1" and p["t_ms"] == 7, p)
m = s.mark(); s.send({"type": "snapshot.request", "request_id": "pie-snap"})
r = s.wait(lambda o: o.get("type") == "snapshot.reply", m)
check("snapshot.reply with airrefueler/1 restore", r and r.get("restore", {}).get("format") == "airrefueler/1", r)
for msg in ({"type": "pod.hose", "seq": 1, "t_ms": 1, "pod": "RIGHT", "payout_ft": 79, "attached": False, "cut": False},
            {"type": "pod.fluid", "pod": "RIGHT", "fuel_pressure_psi": 50, "flow_lb_min": 2800},
            {"type": "camera.lens", "pod": "RIGHT", "lens": "NARROW"},
            {"type": "receiver.add", "id": "TIGER1", "receiver_type": "RAFALE", "behind": "LEFT"}):
    s.send(msg)
m = s.mark(); s.send({"type": "clock.set", "scale": 2, "paused": False})
c = s.state(lambda o: o["clock"]["scale"] == 2, m)
check("clock.set 2 -> time dilation 2", c, "")
m = s.mark(); s.send({"type": "clock.set", "scale": 1, "paused": False})
check("clock.set 1 -> back to 1", s.state(lambda o: o["clock"]["scale"] == 1, m), "")
time.sleep(1.0)
states = [o for _, _, o, _ in s.frames() if o and o.get("type") == "world.state"]
if len(states) > 30:
    span = (states[-1]["t_ms"] - states[0]["t_ms"]) or 1
errors = [schema.errors(o)[:3] for _, op, o, _ in s.frames() if o and schema.errors(o)]
check("every message from AirRefueler matches the schema", not errors, errors[:3])
frames = s.frames()
t0, t1 = frames[0][0], frames[-1][0]
rate = len(states) / max(1e-6, t1 - t0)
check("world.state at ~60 Hz", 50 < rate < 70, round(rate, 1))
s.close()
out = {"checks": checks, "passed": sum(c["ok"] for c in checks), "total": len(checks), "last_state": states[-1] if states else None, "rate_hz": round(rate, 1)}
res = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Results")
os.makedirs(res, exist_ok=True)
json.dump(out, open(os.path.join(res, "pie_check.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
