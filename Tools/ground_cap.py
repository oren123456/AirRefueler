"""Writes Data/Generated/ground_cap.obj: a curved ground cap (planet radius 6360 km, radius 300 km, rings denser
near the centre), Z-up, cm. Imported by Content/Python/ground_setup.py."""
import math, os
R = 6360e5
rings = [0.0] + [300e5 * ((i / 56) ** 2.2) for i in range(1, 57)]
seg = 128
v, n, f = [(0, 0, 0)], [(0, 0, 1)], []
for r in rings[1:]:
    z = -(R - math.sqrt(R * R - r * r))
    for k in range(seg):
        a = 2 * math.pi * k / seg
        x, y = r * math.cos(a), r * math.sin(a)
        v.append((x, y, z)); n.append((x / R, y / R, (R + z) / R))   # UE imports this OBJ as-is (Z up, Y mirrored)
idx = lambda ring, k: 2 + (ring - 1) * seg + (k % seg)
for k in range(seg):
    f.append((1, idx(1, k + 1), idx(1, k)))
for ring in range(1, len(rings) - 1):
    for k in range(seg):
        a, b, c, d = idx(ring, k), idx(ring, k + 1), idx(ring + 1, k + 1), idx(ring + 1, k)
        f += [(a, b, c), (a, c, d)]
out = os.path.join(os.path.dirname(__file__), "..", "Data", "Generated", "ground_cap.obj")
with open(out, "w") as o:
    o.write("# curved ground cap, planet R 6360 km, radius 300 km, cm\n")
    for p in v: o.write("v %.1f %.1f %.1f\n" % p)
    for p in n: o.write("vn %.6f %.6f %.6f\n" % p)
    o.write("vt 0 0\n")
    for t in f: o.write("f %d/1/%d %d/1/%d %d/1/%d\n" % (t[0], t[0], t[1], t[1], t[2], t[2]))
print(len(v), "verts", len(f), "tris ->", out)
