"""UFCP (HUD control box face) decal: 2048^2 colour / normal / mask, face coords s (0..14.02 cm, pilot L->R), t (0..13.61 cm, bottom->top).
Knob positions measured from the mesh / original atlas. Outputs T_UFCP_Color.png (sRGB RGBA), T_UFCP_Normal.png, T_UFCP_Mask.png (R emissive, G roughness)."""
import numpy as np, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy import ndimage
N = 2048; W, H = 14.02, 13.61
sx, sy = N / W, N / H
FB = "/usr/local/lib/python3.13/site-packages/matplotlib/mpl-data/fonts/ttf/DejaVuSans-Bold.ttf"
def P(s, t): return (s * sx, (H - t) * sy)
rng = np.random.default_rng(7)
WHITE = (0.80, 0.79, 0.74)
# ---------------- layers (float)
col = np.zeros((N, N, 3), np.float32)
hgt = np.zeros((N, N), np.float32)
emi = np.zeros((N, N), np.float32)
rgh = np.full((N, N), 0.58, np.float32)
yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
def noise(cell, seed):
    r = np.random.default_rng(seed); g = r.random((N // cell + 3, N // cell + 3)).astype(np.float32)
    return ndimage.zoom(g, cell, order=3)[:N, :N]
n1, n2, n3, n4 = noise(256, 1), noise(64, 2), noise(16, 3), noise(4, 4)
gr = np.clip(0.5 * n1 + 0.3 * n2 + 0.15 * n3 + 0.05 * n4, 0, 1)
khaki = np.array([0.215, 0.195, 0.135], np.float32)
col[:] = khaki * (0.7 + 0.36 * gr[..., None])
# dirt toward the box edges and the bottom
ed = np.minimum(np.minimum(xx, N - 1 - xx), np.minimum(yy, N - 1 - yy)) / sx    # cm to edge
col *= (1.0 - 0.32 * np.exp(-ed / 0.9) * (0.6 + 0.8 * n2))[..., None]
rgh += 0.1 * (n2 - 0.5)
# chipped edges: dark primer / bare metal
chip = (ed < 0.06 + 0.12 * n3) & (n2 + 0.4 * n4 > 0.8)
col[chip] = col[chip] * 0.35 + np.array([0.33, 0.33, 0.31], np.float32) * 0.65; rgh[chip] = 0.38
def L(mask_img): return np.asarray(mask_img, np.float32) / 255.0
def canvas(): im = Image.new("L", (N, N), 0); return im, ImageDraw.Draw(im)
leg = np.zeros((N, N), np.float32)   # backlit legend mask (white paint) -> mask B
def blend(m, c, a=1.0):
    m = m * a; col[:] = col * (1 - m[..., None]) + np.array(c, np.float32) * m[..., None]
    if tuple(c) == tuple(WHITE): leg[:] = np.maximum(leg, m)
# ---------------- knobs (geometry) -> grime rings + finger wear
toggles = [(1.41, 5.91), (3.86, 5.91), (10.07, 5.91), (3.86, 3.01), (9.97, 2.90)]
rotaries = [(1.47, 2.87, 0.70), (12.33, 4.30, 0.72)]
for (s, t) in toggles + [(a, b) for a, b, _ in rotaries]:
    cx, cy = P(s, t); rr = np.hypot((xx - cx) / sx, (yy - cy) / sy)
    ring = np.exp(-((rr - 0.62) / 0.16) ** 2) * (0.7 + 0.6 * n3)
    col *= (1 - 0.35 * ring)[..., None]
    wear = np.exp(-((rr - 0.95) / 0.4) ** 2) * np.clip((n2 - 0.35) * 1.5, 0, 1) * 0.12
    col[:] = col + (np.array([0.42, 0.40, 0.33], np.float32) - col) * wear[..., None]; rgh -= 0.18 * wear / 0.18 * 0.5
# ---------------- engraved lines (border + zone separators)
im, d = canvas()
ins = 0.16
d.rectangle([P(ins, H - ins), P(W - ins, ins)], outline=255, width=5)
for s in (5.07, 9.15):
    d.line([P(s, 0.9), P(s, 8.05)], fill=255, width=5)
d.line([P(ins, 8.15), P(W - ins, 8.15)], fill=255, width=5)
eng = L(im.filter(ImageFilter.GaussianBlur(1.2)))
hgt -= 0.6 * eng; col *= (1 - 0.55 * eng)[..., None]
# ---------------- centre display module (raised bezel + two LCD windows)
m0, m1 = (5.22, 7.75), (8.85, 4.95)
im, d = canvas(); d.rounded_rectangle([P(*m0), P(*m1)], radius=int(0.18 * sx), fill=255)
bez = L(im.filter(ImageFilter.GaussianBlur(2)))
blend(bez, (0.018, 0.018, 0.017)); hgt += 0.8 * bez; rgh = rgh * (1 - bez) + 0.78 * bez
lab = []   # (text, s, t, size_cm, colour, anchor)
def window(t0, t1, value, label):
    im, d = canvas(); d.rectangle([P(6.45, t1), P(8.6, t0)], fill=255)
    w = L(im); blend(w, (0.004, 0.008, 0.005)); hgt[:] -= 0.5 * w; rgh[:] = rgh * (1 - w) + 0.2 * w
    # 7-segment digits
    seg = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd", "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abcdfg", "-": "g", " ": ""}
    dw, dh, th = 0.38, (t1 - t0) * 0.62, 0.065
    x = 6.62; yc = (t0 + t1) / 2
    on, _ = canvas(); dn = ImageDraw.Draw(on); off, _ = canvas(); do = ImageDraw.Draw(off)
    for ch in value:
        segs = {"a": ((x, yc + dh / 2), (x + dw, yc + dh / 2)), "g": ((x, yc), (x + dw, yc)), "d": ((x, yc - dh / 2), (x + dw, yc - dh / 2)),
                "f": ((x, yc), (x, yc + dh / 2)), "b": ((x + dw, yc), (x + dw, yc + dh / 2)), "e": ((x, yc - dh / 2), (x, yc)), "c": ((x + dw, yc - dh / 2), (x + dw, yc))}
        for k, (a, b) in segs.items():
            # slight italic + gap at the joints
            sh = lambda p: (p[0] + 0.12 * (p[1] - yc), p[1])
            a2, b2 = sh(a), sh(b)
            if a[0] == b[0]: a2, b2 = (a2[0], a2[1] + 0.035 * (1 if b[1] > a[1] else -1)), (b2[0], b2[1] - 0.035 * (1 if b[1] > a[1] else -1))
            else: a2, b2 = (a2[0] + 0.035, a2[1]), (b2[0] - 0.035, b2[1])
            (dn if k in seg[ch] else do).line([P(*a2), P(*b2)], fill=255, width=int(th * sx))
        x += dw + 0.13
    onm = L(on.filter(ImageFilter.GaussianBlur(1.0))); offm = L(off.filter(ImageFilter.GaussianBlur(1.0)))
    blend(offm, (0.012, 0.025, 0.014)); blend(onm, (0.35, 1.0, 0.42)); emi[:] = np.maximum(emi, onm)
    glow = L(on.filter(ImageFilter.GaussianBlur(10))) * w
    emi[:] = np.maximum(emi, 0.025 * glow / max(glow.max(), 1e-6))
    lab.append((label, 5.32, (t0 + t1) / 2, 0.22, WHITE, "lm"))
window(6.55, 7.4, "1500", "BINGO")
window(5.3, 6.15, "1013", "QNH")
for (s, t) in ((5.33, 7.57), (8.67, 7.57), (5.33, 5.13), (8.67, 5.13)):    # bezel screws drawn below with the others
    pass
# ---------------- push buttons CLEAR / CCTL (painted domes)
btn = [(5.95, 3.85, "CLEAR"), (8.05, 3.85, "CCTL")]
for (s, t, txt) in btn:
    cx, cy = P(s, t); rr = np.hypot((xx - cx) / sx, (yy - cy) / sy)
    collar = np.clip((0.56 - rr) / 0.02, 0, 1); cap = np.clip((0.42 - rr) / 0.02, 0, 1)
    blend(collar, (0.02, 0.02, 0.019)); blend(cap, (0.035, 0.035, 0.034))
    dome = np.sqrt(np.clip(1 - (rr / 0.42) ** 2, 0, 1))
    hgt += collar * 0.7 + cap * 0.9 * dome; rgh[:] = rgh * (1 - collar) + 0.6 * collar
    col *= (1 - 0.35 * np.exp(-((rr - 0.6) / 0.08) ** 2))[..., None]
    lab.append((txt, s, t - 0.82, 0.24, WHITE, "mm"))
# ---------------- STBY SIGHT placard (black plate, white text, arrows)
im, d = canvas(); d.rounded_rectangle([P(5.25, 2.45), P(8.75, 1.55)], radius=int(0.08 * sx), fill=255)
pl = L(im.filter(ImageFilter.GaussianBlur(1.5))); blend(pl, (0.015, 0.015, 0.015)); hgt += 0.35 * pl; rgh[:] = rgh * (1 - pl) + 0.8 * pl
lab.append(("STBY SIGHT", 7.0, 2.0, 0.24, WHITE, "mm"))
im, d = canvas()
for s in (5.55, 8.45):
    d.polygon([P(s - 0.17, 2.12), P(s + 0.17, 2.12), P(s, 1.8)], fill=255); d.line([P(s, 2.32), P(s, 2.1)], fill=255, width=int(0.07 * sx))
blend(L(im.filter(ImageFilter.GaussianBlur(0.8))), WHITE)
# ---------------- toggle legends
def toggle(s, t, name, up, dn, side=1):
    lab.append((name, s, t + 0.98, 0.26, WHITE, "mm"))
    a = "lm" if side > 0 else "rm"
    lab.append((up, s + side * 0.8, t + 0.4, 0.19, WHITE, a)); lab.append((dn, s + side * 0.8, t - 0.4, 0.19, WHITE, a))
    im, d = canvas()   # position ticks
    for dy in (0.4, -0.4): d.line([P(s + side * 0.6, t + dy), P(s + side * 0.74, t + dy)], fill=255, width=int(0.04 * sx))
    blend(L(im), WHITE)
toggle(1.41, 5.91, "DECLT", "ON", "OFF")
toggle(3.86, 5.91, "RAD ALT", "ON", "OFF")
toggle(10.07, 5.91, "SBY RET", "ON", "OFF")
toggle(3.86, 3.01, "TEST", "ON", "OFF")
toggle(9.97, 2.90, "MODE", "DAY", "NGT", side=-1)
# ---------------- rotary scales
def rotary(s, t, r, name, marks, a0, a1, name_off):
    im, d = canvas()
    n = len(marks)
    for i, m in enumerate(marks):
        a = math.radians(a0 + (a1 - a0) * i / (n - 1))
        p0 = (s + (r + 0.12) * math.cos(a), t + (r + 0.12) * math.sin(a)); p1 = (s + (r + 0.32) * math.cos(a), t + (r + 0.32) * math.sin(a))
        d.line([P(*p0), P(*p1)], fill=255, width=int(0.045 * sx))
        lab.append((m, s + (r + 0.55) * math.cos(a), t + (r + 0.55) * math.sin(a), 0.2, WHITE, "mm"))
        if i < n - 1:   # minor ticks
            am = math.radians(a0 + (a1 - a0) * (i + 0.5) / (n - 1))
            d.line([P(s + (r + 0.12) * math.cos(am), t + (r + 0.12) * math.sin(am)), P(s + (r + 0.22) * math.cos(am), t + (r + 0.22) * math.sin(am))], fill=255, width=int(0.03 * sx))
    blend(L(im.filter(ImageFilter.GaussianBlur(0.6))), WHITE)
    lab.append((name, s + name_off[0], t + name_off[1], 0.26, WHITE, "mm"))
rotary(1.47, 2.87, 0.84, "BRT", ["OFF", "1", "2", "3", "4", "MAX"], 125, -25, (0.0, -1.45))
rotary(12.33, 4.30, 0.86, "DEP", ["0", "5", "10", "15", "25", "40"], 220, -40, (0.0, 1.62))
# ---------------- text
im, d = canvas()
for (txt, s, t, size, c, anc) in lab:
    f = ImageFont.truetype(FB, int(size * sx * 1.36))
    # condensed: draw on a temp image and squeeze x by 0.82
    bb = d.textbbox((0, 0), txt, font=f, anchor="ls")
    tw, th = bb[2] - bb[0] + 8, int(size * sx * 1.8)
    tmp = Image.new("L", (tw, th), 0); ImageDraw.Draw(tmp).text((4, int(th * 0.78)), txt, font=f, fill=255, anchor="ls")
    tmp = tmp.resize((max(1, int(tw * 0.84)), th), Image.LANCZOS)
    x, y = P(s, t); cap = size * sy
    ox = 0 if anc[0] == "l" else (-tmp.width if anc[0] == "r" else -tmp.width // 2)
    im.paste(255, (int(x + ox), int(y - th * 0.78 + cap / 2)), tmp)
txt = L(im)
# paint wear on the legends
wearholes = (n4 > 0.82) & (n3 > 0.5)
txt = txt * np.where(wearholes, 0.35, 1.0) * (0.85 + 0.15 * n2)
blend(txt, WHITE); rgh[:] = rgh * (1 - txt) + 0.62 * txt
# ---------------- screws (bezel, placard) + Dzus fasteners (corners)
def screw(s, t, R, dzus=False):
    cx, cy = P(s, t); rr = np.hypot((xx - cx) / sx, (yy - cy) / sy); dx = (xx - cx) / sx; dy = (yy - cy) / sy
    m = np.clip((R - rr) / 0.015, 0, 1)
    if not m.any(): return
    shade = np.clip(0.34 + 0.18 * (-dx - dy) / R, 0.18, 0.55)
    c = np.stack([shade, shade * 0.98, shade * 0.93], -1)
    col[:] = col * (1 - m[..., None]) + c * m[..., None]
    col[:] *= (1 - 0.5 * np.exp(-((rr - R - 0.02) / 0.03) ** 2))[..., None]
    ang = 0.6 if dzus else 0.0
    ca, sa = math.cos(ang), math.sin(ang)
    u, v = dx * ca + dy * sa, -dx * sa + dy * ca
    slot = ((np.abs(v) < 0.025) & (rr < R * 0.8)) if dzus else (((np.abs(u) < 0.022) | (np.abs(v) < 0.022)) & (rr < R * 0.6))
    col[slot] *= 0.25
    hgt[:] += m * 0.9 * np.sqrt(np.clip(1 - (rr / R) ** 2, 0, 1)) - slot * 0.4
    rgh[:] = rgh * (1 - m) + 0.35 * m
for (s, t) in ((5.33, 7.57), (8.67, 7.57), (5.33, 5.13), (8.67, 5.13)): screw(s, t, 0.09)
for (s, t) in ((0.48, 0.48), (W - 0.48, 0.48), (0.48, 7.75), (W - 0.48, 7.75)): screw(s, t, 0.2, dzus=True)
for s in (2.6, 11.4): screw(s, 0.48, 0.11)
# ---------------- scratches + grime overlay
im, d = canvas()
for _ in range(700):
    x, y = rng.uniform(0, N), rng.uniform(N * 0.35, N); a = rng.uniform(0, math.pi); Lc = rng.uniform(0.1, 0.6) * sx
    d.line([(x, y), (x + Lc * math.cos(a), y + Lc * math.sin(a))], fill=int(rng.uniform(60, 160)), width=2)
sc = L(im) * (1 - bez)
col[:] = col + (np.array([0.45, 0.43, 0.37], np.float32) - col) * (0.4 * sc)[..., None]
col *= (0.92 + 0.12 * n3)[..., None]
# ---------------- outputs
srgb = lambda x: np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(np.clip(x, 0, 1), 1 / 2.4) - 0.055)
rgba = np.dstack([srgb(np.clip(col, 0, 1)), np.ones((N, N), np.float32)])
Image.fromarray((rgba * 255 + 0.5).astype(np.uint8), "RGBA").save("/tmp/ufcp/T_UFCP_Color.png")
hs = ndimage.gaussian_filter(hgt, 1.0)
gx = ndimage.sobel(hs, 1) / 8.0; gy = ndimage.sobel(hs, 0) / 8.0
k = 2.5
nv = np.dstack([-gx * k, gy * k, np.ones_like(hs)]); nv /= np.linalg.norm(nv, axis=2, keepdims=True)
Image.fromarray(((nv * 0.5 + 0.5) * 255 + 0.5).astype(np.uint8)).save("/tmp/ufcp/T_UFCP_Normal.png")
mk = np.dstack([np.clip(emi, 0, 1), np.clip(rgh, 0.03, 1), np.clip(ndimage.gaussian_filter(leg, 1.0) * 1.2, 0, 1)])
Image.fromarray((mk * 255 + 0.5).astype(np.uint8)).save("/tmp/ufcp/T_UFCP_Mask.png")
prev = Image.fromarray((rgba[..., :3] * 255).astype(np.uint8)).resize((1024, 1024), Image.LANCZOS)
prev.save("/tmp/ufcp/preview.jpg", quality=90)
print("ok")
