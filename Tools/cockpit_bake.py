"""Bake Mirage-style weathering into the cockpit atlas: khaki HUD-control box, edge wear + grime + scratches on
the front panel plates, Phillips screws around instruments (placed in 3D, projected to UV), screw normal map."""
import json, numpy as np, math, sys
from PIL import Image, ImageDraw
from scipy import ndimage
Image.MAX_IMAGE_PIXELS = None
S = 8192
d = json.load(open("/mnt/user-data/uploads/AirRefueler/Saved/ClaudeShots/cockpit_tris.json"))
atlas = np.load("/tmp/atlas.npy")   # uint8
rng = np.random.default_rng(3)

# ---------- front triangles
tris = []   # (mesh, P[3x3], UV[3x2])
for name in ("Devices", "Cockpit_Panel", "Control_Device", "Cockpit"):
    m = d["meshes"][name]; P = np.array(m["pos"]); UV = np.array(m["uv"]); T = np.array(m["tri"]).reshape(-1, 3)
    for t in T:
        if P[t][:, 1].mean() > -4640: tris.append((name, P[t], UV[t]))
print("front tris", len(tris))
# rasterise triangle ids
tid = Image.new("I", (S, S), 0); dr = ImageDraw.Draw(tid)
for i, (nm, P, UV) in enumerate(tris):
    dr.polygon([tuple(q * S) for q in UV], fill=i + 1)
tid = np.asarray(tid, dtype=np.int32)
cover = tid > 0
print("covered px", cover.sum())
# per-triangle info
cen = np.array([P.mean(0) for _, P, _ in tris])
nrm = np.array([np.cross(P[1] - P[0], P[2] - P[0]) for _, P, _ in tris]); nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-9)

# exclude instrument faces / displays (atlas islands with purple outline + counter + displays)
isl = json.load(open("/mnt/user-data/uploads/AirRefueler/Saved/ClaudeShots/islands_atlas.json")) if False else None
excl = np.zeros((S, S), bool)
for (x, y, w, h) in [(1078,1953,40,68),(1160,1953,38,70),(1324,1963,38,70),(3610,4936,146,148),(6466,4223,64,60),(1894,7359,64,62),(3814,7439,86,84),(3610,7561,62,60),(3814,7573,86,84),(2066,6186,44,78),(1446,6143,48,46),(2874,7129,50,46),(3078,7210,50,48),(180,3677,40,95),(426,3868,38,96),(1270,3270,50,140),(6752,6868,86,85),(916,5028,116,118)]:
    excl[max(0, y - 4):y + h + 4, max(0, x - 4):x + w + 4] = True

out = atlas.copy()
lum = (atlas[..., 0].astype(np.uint16) + atlas[..., 1] + atlas[..., 2]) // 3   # 0..255
def noise_at(ys, xs, cell, seed):
    r = np.random.default_rng(seed); g = r.random((S // cell + 3, S // cell + 3)).astype(np.float32)
    return ndimage.map_coordinates(g, [ys / cell, xs / cell], order=3, mode="nearest")
def get(mask): return out[mask].astype(np.float32) / 255.0
def put(mask, v): out[mask] = (np.clip(v, 0, 1) * 255 + 0.5).astype(np.uint8)

# ---------- khaki HUD-control box (Devices triangles in the box volume, facing out)
boxtri = np.zeros(len(tris) + 1, bool)
for i, (nm, P, UV) in enumerate(tris):
    c = cen[i]
    if nm == "Devices" and -1752 < c[0] < -1702 and -4566 < c[1] < -4522 and 224 < c[2] < 255: boxtri[i + 1] = True
box = boxtri[tid] & ~excl
print("box px", box.sum())
khaki = np.array([0.30, 0.275, 0.205], np.float32)
bl = box & (lum < 82)                        # keep printed white labels
ys, xs = np.nonzero(bl)
gr = np.clip(0.55 * noise_at(ys, xs, 64, 1) + 0.3 * noise_at(ys, xs, 16, 2) + 0.15 * noise_at(ys, xs, 4, 3), 0, 1)
t = (lum[bl].astype(np.float32) / 255.0 / 0.12)[:, None]
bd = ndimage.distance_transform_cdt(box, metric='taxicab')[bl].astype(np.float32)
kc = khaki * np.clip(t, 0.7, 1.3) * (0.55 + 0.55 * gr[:, None]) * (1.0 - 0.35 * np.exp(-bd / 25.0))[:, None]   # grimy, dirt toward the edges
kc = kc + (np.array([0.5, 0.48, 0.42], np.float32) - kc) * (0.6 * np.clip(1.0 - bd / 2.5, 0, 1) * (noise_at(ys, xs, 16, 5) > 0.45))[:, None]   # worn metal edges
put(bl, kc)
# ---------- edge distance (island boundary) for wear/grime on the plates
plate = cover & ~excl
dist = ndimage.distance_transform_cdt(plate, metric="chessboard").astype(np.float32) if False else ndimage.distance_transform_cdt(plate, metric="taxicab")
pl = plate & (lum < 115) & ~box
ys, xs = np.nonzero(pl)
dd = dist[pl].astype(np.float32); del dist
n1 = noise_at(ys, xs, 64, 1); n2 = noise_at(ys, xs, 16, 2); n3 = noise_at(ys, xs, 4, 3)
gr = np.clip(0.55 * n1 + 0.3 * n2 + 0.15 * n3, 0, 1)
edge = np.clip(1.0 - dd / 2.6, 0, 1) * (n2 > 0.36)
corner = np.exp(-dd / 18.0)
wearcol = np.array([0.36, 0.36, 0.34], np.float32)
o = get(pl)
o = 0.045 + 0.4 * o                                                         # charcoal plates (Mirage)
o = o * (1.0 - 0.38 * (corner * gr)[:, None])
o = o * (0.9 + 0.2 * n1[:, None])
o = o + (wearcol - o) * (0.65 * edge[:, None])
# scratches
sc = Image.new("L", (S, S), 0); sd = ImageDraw.Draw(sc)
sub = rng.choice(len(xs), size=min(9000, len(xs)), replace=False)
for k in sub:
    x, y = xs[k], ys[k]; a_ = rng.uniform(0, math.pi); L = rng.uniform(3, 14)
    sd.line([(x, y), (x + L * math.cos(a_), y + L * math.sin(a_))], fill=int(rng.uniform(40, 110)), width=1)
scv = np.asarray(sc)[pl].astype(np.float32) / 255.0; del sc
o = o + (np.array([0.5, 0.5, 0.48], np.float32) - o) * (0.35 * scv[:, None])
put(pl, o)
del o, n1, n2, n3, gr, edge, corner, scv, ys, xs
# ---------- screws around instruments (3D placement -> UV)
inst = json.load(open("/tmp/bake/inst3d.json"))
nrmN = np.zeros((S, S, 3), np.uint8); nrmN[..., 0] = 128; nrmN[..., 1] = 128; nrmN[..., 2] = 255
cand = [i for i, (nm, P, UV) in enumerate(tris) if nm in ("Devices", "Cockpit_Panel")]
def to_uv(p):
    best = None
    for i in cand:
        _, P, UV = tris[i]
        n = nrm[i]; dd = np.dot(p - P[0], n)
        if abs(dd) > 1.2: continue
        q = p - dd * n
        v0, v1, v2 = P[1] - P[0], P[2] - P[0], q - P[0]
        d00, d01, d11, d20, d21 = v0 @ v0, v0 @ v1, v1 @ v1, v2 @ v0, v2 @ v1
        den = d00 * d11 - d01 * d01
        if abs(den) < 1e-9: continue
        b1 = (d11 * d20 - d01 * d21) / den; b2 = (d00 * d21 - d01 * d20) / den
        if b1 < -0.01 or b2 < -0.01 or b1 + b2 > 1.01: continue
        if best is None or abs(dd) < best[0]:
            uv = UV[0] + b1 * (UV[1] - UV[0]) + b2 * (UV[2] - UV[0])
            best = (abs(dd), uv, i)
    return best
placed = 0
yy, xx = np.mgrid[-8:9, -8:9].astype(np.float32)
for g in inst:
    c = np.array(g["p"]); n = np.array(g["n"]); n /= np.linalg.norm(n)
    up = np.array([0, 0, 1.0]) - n * n[2]; up /= np.linalg.norm(up); rt = np.cross(n, up)
    pts = []
    if g["kind"] == "round":
        for a in (45, 135, 225, 315):
            pts.append(c + (rt * math.cos(math.radians(a)) + up * math.sin(math.radians(a))) * g["r"] * 1.32)
    else:
        hw, hh = g["hw"] + 0.75, g["hh"] + 0.75
        for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)): pts.append(c + rt * sx * hw + up * sy * hh)
    for p in pts:
        h = to_uv(p)
        if h is None: continue
        uv = h[1] * S; cx, cy = uv
        x0, y0 = int(round(cx)), int(round(cy))
        if excl[y0, x0]: continue
        R = 4.6                                    # ~0.42 cm at 10.8 px/cm
        dx, dy = xx + (x0 - cx), yy + (y0 - cy); rr = np.sqrt(dx * dx + dy * dy)
        head = np.clip(R - rr, 0, 1)[..., None]
        ring = np.clip(1.0 - np.abs(rr - R - 0.6), 0, 1)[..., None]
        slot = (((np.abs(dx) < 0.7) | (np.abs(dy) < 0.7)) & (rr < R * 0.75)).astype(np.float32)[..., None]
        shade = np.clip(0.36 + 0.12 * (-dx - dy) / R, 0.2, 0.5)[..., None]
        reg = out[y0 - 8:y0 + 9, x0 - 8:x0 + 9].astype(np.float32) / 255.0
        reg = reg * (1 - 0.6 * ring)
        reg = reg * (1 - head) + head * (shade * np.array([1.0, 0.98, 0.93]))
        reg = reg * (1 - 0.8 * slot * head)
        out[y0 - 8:y0 + 9, x0 - 8:x0 + 9] = (np.clip(reg, 0, 1) * 255 + 0.5).astype(np.uint8)
        # normal: domed head
        z = np.sqrt(np.clip(1 - (rr / R) ** 2, 0, 1))
        nx = np.where(rr < R, dx / R * 0.8, 0); ny = np.where(rr < R, dy / R * 0.8, 0)
        nv = np.stack([nx, ny, np.maximum(z, 0.3)], -1); nv /= np.linalg.norm(nv, axis=2, keepdims=True)
        m = (rr < R)[..., None]
        nreg = nrmN[y0 - 8:y0 + 9, x0 - 8:x0 + 9]
        nrmN[y0 - 8:y0 + 9, x0 - 8:x0 + 9] = np.where(m, ((nv * 0.5 + 0.5) * 255 + 0.5).astype(np.uint8), nreg)
        placed += 1
print("screws placed", placed)
Image.fromarray(out).save("/tmp/bake/T_Salon_Diffuse_Mirage.png")
Image.fromarray(nrmN).save("/tmp/bake/T_Salon_Normal_Mirage.png")
print("saved")
