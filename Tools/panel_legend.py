"""Panel legend glow mask: white printed labels on the front panel plates (atlas lum > 115, outside instrument faces,
displays and the khaki box), small connected blobs only -> 4096^2 L8 (T_PanelLegend, emissive mask)."""
import json, numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
Image.MAX_IMAGE_PIXELS = None
S = 8192
d = json.load(open("/mnt/user-data/uploads/AirRefueler/Saved/ClaudeShots/cockpit_tris.json"))
atlas = np.load("/tmp/atlas.npy", mmap_mode="r")
tris = []
for name in ("Devices", "Cockpit_Panel", "Control_Device", "Cockpit"):
    m = d["meshes"][name]; P = np.array(m["pos"]); UV = np.array(m["uv"]); T = np.array(m["tri"]).reshape(-1, 3)
    for t in T:
        if P[t][:, 1].mean() > -4640: tris.append((name, P[t], UV[t]))
# legends are printed on the panel plates only (Devices / Cockpit_Panel); knobs & switches (Control_Device) excluded
tris = [x for x in tris if x[0] in ("Devices", "Cockpit_Panel") and np.linalg.norm(np.cross(x[1][1] - x[1][0], x[1][2] - x[1][0])) / 2 > 4.0]  # big flat plate faces, not knob caps
tid = Image.new("I", (S, S), 0); dr = ImageDraw.Draw(tid)
for i, (nm, P, UV) in enumerate(tris): dr.polygon([tuple(q * S) for q in UV], fill=i + 1)
tid = np.asarray(tid, dtype=np.int32); cover = tid > 0
cen = np.array([P.mean(0) for _, P, _ in tris])
excl = np.zeros((S, S), bool)
for (x, y, w, h) in [(1078,1953,40,68),(1160,1953,38,70),(1324,1963,38,70),(3610,4936,146,148),(6466,4223,64,60),(1894,7359,64,62),(3814,7439,86,84),(3610,7561,62,60),(3814,7573,86,84),(2066,6186,44,78),(1446,6143,48,46),(2874,7129,50,46),(3078,7210,50,48),(180,3677,40,95),(426,3868,38,96),(1270,3270,50,140),(6752,6868,86,85),(916,5028,116,118)]:
    excl[max(0, y - 4):y + h + 4, max(0, x - 4):x + w + 4] = True
boxtri = np.zeros(len(tris) + 1, bool)
for i, (nm, P, UV) in enumerate(tris):
    c = cen[i]
    if nm == "Devices" and -1752 < c[0] < -1702 and -4566 < c[1] < -4522 and 224 < c[2] < 255: boxtri[i + 1] = True
box = boxtri[tid]; del tid
lum = (atlas[..., 0].astype(np.uint16) + atlas[..., 1] + atlas[..., 2]) // 3
sat = atlas.max(2).astype(np.int16) - atlas.min(2)
lab = cover & ~excl & ~box & (lum > 85) & (sat < 60)      # white-ish paint only (no red/amber lamps)
del lum, sat, cover
L, n = ndimage.label(lab)
area = ndimage.sum(lab, L, index=np.arange(1, n + 1))
sl = ndimage.find_objects(L)
keep = np.zeros(n + 1, bool)
for k in range(n):
    h = sl[k][0].stop - sl[k][0].start; w = sl[k][1].stop - sl[k][1].start
    keep[k + 1] = area[k] <= 70 and max(h, w) <= 12          # glyphs / short tick marks, not large light areas
# thin strokes only: drop components whose interior is thicker than lettering (knob caps, screw heads, dots)
dt = ndimage.distance_transform_edt(lab)
thick = ndimage.maximum(dt, L, index=np.arange(1, n + 1))
keep[1:] &= thick <= 2.3
del dt
m = keep[L]; del L
dens = ndimage.uniform_filter(m.astype(np.float32), 200)
m &= dens < 0.3                                            # drop dense textures (tread-plate hatch), keep sparse lettering
del dens
m[3940:6100, 3940:4900] = False                           # floor tread-plate island
m[3060:3200, 6140:6240] = False                           # dot grid (not lettering)
print("label px", lab.sum(), "kept", m.sum(), "components", n, "kept comps", keep.sum())
# soft intensity from original brightness, 2x2 box downsample to 4096
v = np.where(m, 1.0, 0.0).astype(np.float32)
v = v.reshape(4096, 2, 4096, 2).mean((1, 3))
v = ndimage.gaussian_filter(v, 0.6)
v = np.clip(v * 1.6, 0, 1)
Image.fromarray((v * 255 + 0.5).astype(np.uint8), "L").save("/tmp/bake/T_PanelLegend.png")
prev = Image.fromarray((v * 255).astype(np.uint8)).resize((2048, 2048), Image.BOX); prev.save("/tmp/bake/legend_prev.png")
print("saved")
