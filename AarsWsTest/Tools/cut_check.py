import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import contract_test
s = contract_test.Session(9100)
s.wait(lambda o: o.get("type") == "hello", 0, 3.0)
s.send({"type": "hello", "role": "sim", "name": "cut-check", "version": "0.2"})
before = s.state(lambda o: True, 0, 2.0)
seq = int(time.time() * 1000) % 1000000000
for i in range(90):
    seq += 1
    s.send({"type": "pod.hose", "seq": seq, "t_ms": i * 16, "pod": "LEFT", "payout_ft": 30, "attached": False, "cut": True})
    time.sleep(1 / 60)
after = s.state(lambda o: True, s.mark(), 2.0)
for i in range(30):   # cut is permanent: paying out again must not bring it back
    seq += 1
    s.send({"type": "pod.hose", "seq": seq, "t_ms": 2000 + i * 16, "pod": "LEFT", "payout_ft": 60, "attached": False, "cut": False})
    time.sleep(1 / 60)
later = s.state(lambda o: True, s.mark(), 2.0)
out = {"before": before["pods"]["LEFT"], "after_cut": after["pods"]["LEFT"], "after_payout_again": later["pods"]["LEFT"]}
json.dump(out, open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Results", "cut_check.json"), "w"))
s.close()
