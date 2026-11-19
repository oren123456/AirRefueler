"""Replace Indian flags / IAF roundels in diffuse textures with Israeli flag / Israeli AF roundel.
usage: python3 israel_markings.py <src_texture> <out_png>   (writes a new file; source untouched)"""
import sys, math
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

BLUE = (0, 56, 184); WHITE = (255, 255, 255)

def hexagram(d, cx, cy, r, fill):
    for a0 in (-90, 90):
        d.polygon([(cx + r * math.cos(math.radians(a0 + k * 120)), cy + r * math.sin(math.radians(a0 + k * 120))) for k in range(3)], fill=fill)

def israel_flag(W=2200, H=1600):
    im = Image.new('RGB', (W, H), WHITE); d = ImageDraw.Draw(im)
    s = H / 160.0
    d.rectangle([0, 15 * s, W, 40 * s], fill=BLUE); d.rectangle([0, 120 * s, W, 145 * s], fill=BLUE)
    cx, cy = W / 2, H / 2; ro = 36.7 * s; t = 5.5 * s           # star of David as two outlined triangles
    ri = ro - 2 * t                                              # inner triangle (inset by line thickness)
    hexagram(d, cx, cy, ro, BLUE); hexagram(d, cx, cy, ri, WHITE)
    # re-draw the outlines where the white inner triangles cut across the other triangle's line
    for a0 in (-90, 90):
        P = [(cx + ro * math.cos(math.radians(a0 + k * 120)), cy + ro * math.sin(math.radians(a0 + k * 120))) for k in range(3)]
        for k in range(3):
            d.line([P[k], P[(k + 1) % 3]], fill=BLUE, width=int(t * 1.0))
    return np.asarray(im)

def roundel(N=1024):
    im = Image.new('RGBA', (N, N), (0, 0, 0, 0)); d = ImageDraw.Draw(im); R = N / 2
    d.ellipse([0, 0, N - 1, N - 1], fill=BLUE + (255,))
    d.ellipse([R * 0.12, R * 0.12, N - 1 - R * 0.12, N - 1 - R * 0.12], fill=WHITE + (255,))
    hexagram(d, R, R, R * 0.70, BLUE + (255,))
    return im

REMOVE_FLAGS = False
def main(src, out, angles=None):
    import json, os
    ang = json.load(open(angles)) if angles and os.path.exists(angles) else {}
    found = []
    img = Image.open(src).convert('RGB'); a = np.array(img); H, W = a.shape[:2]
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    org = (r > 200) & (g > 50) & (g < 150) & (b < 70)
    grn = (g.astype(int) > r.astype(int) + 25) & (g.astype(int) > b.astype(int) + 25) & (g > 40)
    k = max(W, H) / 2048.0
    it = max(2, int(3 * k))
    lo, _ = ndimage.label(ndimage.binary_dilation(org, iterations=it)); lg, _ = ndimage.label(ndimage.binary_dilation(grn, iterations=it))
    gl = [(j, sl) for j, sl in enumerate(ndimage.find_objects(lg), 1) if (lg[sl] == j).sum() >= 15 * k * k]
    gcent = {j: np.array(ndimage.center_of_mass((lg[sl] == j) & grn[sl])) + [sl[0].start, sl[1].start] for j, sl in gl}
    flag_tpl = israel_flag(); rnd_tpl = roundel()
    nf = nr = 0
    for i, osl in enumerate(ndimage.find_objects(lo), 1):
        om = (lo[osl] == i) & org[osl]
        if om.sum() < 40 * k * k:
            continue
        oyx = np.array(ndimage.center_of_mass(om)) + [osl[0].start, osl[1].start]
        osz = max(osl[0].stop - osl[0].start, osl[1].stop - osl[1].start)
        j = min(gcent, key=lambda q: np.linalg.norm(gcent[q] - oyx))
        if np.linalg.norm(gcent[j] - oyx) > 2.5 * osz:
            continue
        gsl = dict(gl)[j]
        pd = 4
        sl = (slice(max(0, min(osl[0].start, gsl[0].start) - pd), min(H, max(osl[0].stop, gsl[0].stop) + pd)),
              slice(max(0, min(osl[1].start, gsl[1].start) - pd), min(W, max(osl[1].stop, gsl[1].stop) + pd)))
        ys, xs = sl
        o = (lo[sl] == i) & org[sl]; gm = (lg[sl] == j) & grn[sl]; sub = o | gm
        oy, ox = np.nonzero(o); gy, gx = np.nonzero(gm)
        oc = np.array([ox.mean(), oy.mean()]); gc = np.array([gx.mean(), gy.mean()])
        py, px = np.nonzero(o | gm)
        size = max(np.ptp(px), np.ptp(py)) + 1
        if np.linalg.norm(oc - gc) < 0.15 * size:          # roundel: green dot centred in orange ring
            cx, cy = xs.start + oc[0], ys.start + oc[1]
            R = np.sqrt(((ox - oc[0]) ** 2 + (oy - oc[1]) ** 2).max()) + 1.5 * k
            D = int(math.ceil(2 * R)); x0 = int(round(cx - R)); y0 = int(round(cy - R))
            key = '%d,%d' % (int(round(cx)), int(round(cy)))
            found.append({'cx': float(cx), 'cy': float(cy), 'R': float(R), 'u': float(cx / W), 'v': float(cy / H)})
            tpl = rnd_tpl
            if key in ang:   # degrees, clockwise in image, star point direction
                tpl = rnd_tpl.rotate(-ang[key], resample=Image.BICUBIC)
            t = tpl.resize((D, D), Image.LANCZOS)
            img.paste(t.convert('RGB'), (x0, y0), t.split()[3]); nr += 1
        else:                                             # flag: stripes, up = green -> saffron
            u = (oc - gc) / np.linalg.norm(oc - gc); rv = np.array([-u[1], u[0]])
            P = np.stack([px - 0, py - 0], 1).astype(float)
            pu = P @ u; pr = P @ rv
            u0, u1 = pu.min() - 0.7 * k, pu.max() + 0.7 * k; r0, r1 = pr.min() - 0.7 * k, pr.max() + 0.7 * k
            # pixel grid of the bbox, 4x supersampled
            hh, ww = sub.shape; ss = 4
            gy2, gx2 = np.mgrid[0:hh * ss, 0:ww * ss]
            X = (gx2 + 0.5) / ss - 0.5; Y = (gy2 + 0.5) / ss - 0.5
            qu = X * u[0] + Y * u[1]; qr = X * rv[0] + Y * rv[1]
            s = (qr - r0) / (r1 - r0); tt = (u1 - qu) / (u1 - u0)   # s: 0..1 across, tt: 0 top..1 bottom
            inside = (s >= 0) & (s <= 1) & (tt >= 0) & (tt <= 1)
            fx = xs.start + (px.mean()); fy = ys.start + (py.mean())
            fkey = 'F%d,%d' % (int(round(fx)), int(round(fy)))
            found.append({'flag': True, 'cx': float(fx), 'cy': float(fy), 'u': float(fx / W), 'v': float(fy / H),
                          'stripe': [float(rv[0]), float(rv[1])], 'key': fkey})
            mode = ang.get(fkey, 0)
            if mode == 'remove' or REMOVE_FLAGS:
                import cv2
                cov = inside.reshape(hh, ss, ww, ss).any(axis=(1, 3))
                pad = int(30 * k)
                Y0, Y1, X0, X1 = max(0, ys.start - pad), min(H, ys.stop + pad), max(0, xs.start - pad), min(W, xs.stop + pad)
                m = np.zeros((Y1 - Y0, X1 - X0), np.uint8)
                m[ys.start - Y0: ys.stop - Y0, xs.start - X0: xs.stop - X0] = cov * 255
                m = cv2.dilate(m, np.ones((5, 5), np.uint8), iterations=max(1, int(k)))
                # fill by copying the band from both sides along the flag's 'up' axis (the fin cheat-line runs that way)
                off = (u1 - u0) + 8 * k
                yy, xx = np.nonzero(m)
                acc = np.zeros((len(yy), 3)); cnt = 0
                for sg in (1, -1):
                    sy_ = np.clip(np.round(yy + Y0 + sg * off * u[1]).astype(int), 0, H - 1)
                    sx_ = np.clip(np.round(xx + X0 + sg * off * u[0]).astype(int), 0, W - 1)
                    acc += a[sy_, sx_].astype(float); cnt += 1
                fixed = a[Y0:Y1, X0:X1].copy()
                mf = cv2.GaussianBlur(m.astype(np.float32) / 255, (0, 0), 1.5)[..., None]
                fill = fixed.astype(float); fill[yy, xx] = acc / cnt
                fixed = (fixed * (1 - mf) + fill * mf).astype(np.uint8)
                a[Y0:Y1, X0:X1] = fixed
                img.paste(Image.fromarray(np.ascontiguousarray(a[Y0:Y1, X0:X1])), (X0, Y0)); nf += 1
                a = np.array(img)
                continue
            ftpl = np.ascontiguousarray(np.rot90(flag_tpl)) if mode == 'rot90' else flag_tpl
            FH, FW = ftpl.shape[:2]
            sx = np.clip((s * (FW - 1)).astype(int), 0, FW - 1); sy = np.clip((tt * (FH - 1)).astype(int), 0, FH - 1)
            col = ftpl[sy, sx].astype(float) * inside[..., None]
            col = col.reshape(hh, ss, ww, ss, 3).mean((1, 3)); al = inside.reshape(hh, ss, ww, ss).mean((1, 3))[..., None]
            region = a[sl].astype(float)
            region = region * (1 - al) + col          # col already premultiplied by coverage
            a[sl] = np.clip(region, 0, 255).astype(np.uint8)
            Image.Image.paste(img, Image.fromarray(a[sl]), (xs.start, ys.start)); nf += 1
        a = np.array(img)
    img.save(out)
    json.dump({'src': src, 'W': W, 'H': H, 'roundels': found}, open(out + '.markings.json', 'w'), indent=1)
    print(src.split('/')[-1], '-> flags', nf, 'roundels', nr)

if __name__ == '__main__':
    if '--remove-flags' in sys.argv:
        sys.argv.remove('--remove-flags'); REMOVE_FLAGS = True
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
