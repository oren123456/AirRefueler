"""Send pod.hose for one pod: ramp from the current payout to <target> ft at 15 ft/s, hold <seconds>.
Usage: hose_hold.py port pod target seconds [cut]"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import contract_test
port, pod, target, secs = int(sys.argv[1]), sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
cut = len(sys.argv) > 5 and sys.argv[5] == "cut"
s = contract_test.Session(port)
s.wait(lambda o: o.get("type") == "hello", 0, 3.0)
s.send({"type": "hello", "role": "sim", "name": "hose-hold", "version": "0.2"})
st = s.state(lambda o: True, 0, 2.0)
start = st["pods"][pod]["tip_ft"] if st else 0.0
t0 = time.perf_counter(); dur = abs(target - start) / 15.0; seq = int(time.time() * 1000) % 1000000000
while True:
    t = time.perf_counter() - t0
    p = target if t >= dur else start + (target - start) * t / dur
    seq += 1
    s.send({"type": "pod.hose", "seq": seq, "t_ms": int(t * 1000), "pod": pod, "payout_ft": round(p, 3), "attached": False, "cut": cut})
    if t >= dur + secs:
        break
    time.sleep(1 / 60)
s.close()
