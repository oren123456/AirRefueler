"""Live instruments on the Mirage front panel, drawn in texture space by the panel material.
M_MayaPBR_Live = copy of M_MayaPBR + two Custom nodes: PanelLive (gauge faces over the atlas islands of the front
panel, data from MPC_HUD) and PanelMask (glass / display-glow masks). Only MI_Salon_VRay1_Cutout ("Devices" mesh)
is re-parented to it. Island centres / UV-per-cm bases come from panel_islands.py + atlas analysis. Re-runnable:
on later runs only the Custom node code and parameters are updated (an in-use material must never be deleted)."""
import unreal
MAT = "/Game/AirRefueler/Materials"; SRC = MAT + "/M_MayaPBR"; DST = MAT + "/M_MayaPBR_Live"
eal = unreal.EditorAssetLibrary; mel = unreal.MaterialEditingLibrary
log = lambda s: unreal.log("[PanelLive] " + s)

LIVE = r"""
struct PF {
  float seg(float2 p, float2 a, float2 b) { float2 pa = p - a, ba = b - a; float h = saturate(dot(pa, ba) / dot(ba, ba)); return length(pa - ba * h); }
  float ln(float d, float w, float aa) { return 1.0 - smoothstep(w, w + aa, d); }
  float2 rot(float2 p, float a) { float c = cos(a), s = sin(a); return float2(c * p.x - s * p.y, s * p.x + c * p.y); }
  float2 dirc(float a) { return float2(sin(a), cos(a)); }            // clockwise from 12 o'clock
  float2 loc(float2 uv, float2 c, float2 eR, float2 eU, float r) {    // uv -> dial coords (radius 1)
    float2 a = eR * r, b = eU * r, d = uv - c; float det = a.x * b.y - a.y * b.x;
    return float2((d.x * b.y - d.y * b.x) / det, (a.x * d.y - a.y * d.x) / det);
  }
  float glyph(Texture2D T, SamplerState S, float2 uv, int c, float2 dx, float2 dy) {
    if (c <= 0 || uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) return 0.0;
    float2 t = (float2(c % 8, c / 8) + float2(uv.x, 1.0 - uv.y)) / 8.0;
    return T.SampleGrad(S, t, float2(dx.x, -dx.y) / 8.0, float2(dy.x, -dy.y) / 8.0).r;
  }
  // one character (code c) centred at o, height h
  float chr(Texture2D T, SamplerState S, float2 p, float2 o, float h, int c, float2 dx, float2 dy) {
    return glyph(T, S, (p - o) / h + 0.5, c, dx / h, dy / h);
  }
  // integer v (>= 0) centred at o, n digits, no leading zeros
  float num(Texture2D T, SamplerState S, float2 p, float2 o, float h, float v, int n, float2 dx, float2 dy) {
    float adv = 0.5 * h; float x0 = o.x - 0.5 * n * adv; int k = (int)floor((p.x - x0) / adv);
    if (k < 0 || k >= n) return 0.0;
    float iv = floor(v + 0.5); float place = floor(pow(10.0, n - 1 - k) + 0.5);
    if (iv < place - 0.5 && k < n - 1) return 0.0;
    float qd = floor(iv / place + 0.01); int dg = (int)(qd - 10.0 * floor(qd / 10.0 + 0.01) + 0.5);
    return glyph(T, S, float2((p.x - x0 - (k + 0.5) * adv) / h + 0.5, (p.y - o.y) / h + 0.5), 16 + clamp(dg, 0, 9), dx / h, dy / h);
  }
};
PF f;
// ---- flight data (MPC_HUD)
float3 F = normalize(AF.xyz); float3 R = normalize(cross(AU.xyz, F)); float3 U = cross(F, R);
float pitch = degrees(asin(clamp(F.z, -1.0, 1.0)));
float roll = degrees(atan2(-R.z, U.z));
float hdg = degrees(atan2(F.y, F.x)); hdg = hdg < 0.0 ? hdg + 360.0 : hdg;
float ias = D0.x, alt = D0.y, gl = D0.z, fuel = D1.z, aoa = D2.z;
float vs = Vel.z / 30.48 * 60.0;                                     // ft/min
float3 col = Base; float glow = 0.0;
float3 FACE = float3(0.018, 0.018, 0.02), INK = float3(0.86, 0.86, 0.82), BEZ = float3(0.025, 0.025, 0.027);
float RB = 1.07;   // dials are drawn out to 1.07 radius: 1.0-1.07 = dark bezel (hides the old art's edge)

// ---- dial coordinates (front panel islands; radius in cm)
float2 pA = f.loc(UV, float2(0.79321, 0.51917), float2(-0.001282, -0.0003699), float2(-0.0003228, 0.0012724), 2.45);   // airspeed
float2 pT = f.loc(UV, float2(0.44446, 0.92664), float2(-0.0003091, -0.0013447), float2(-0.0013758, 0.0002068), 2.25);  // attitude
float2 pH = f.loc(UV, float2(0.47083, 0.91321), float2(-0.0012951, -0.000343), float2(-0.0003638, 0.0011891), 3.35);   // compass
float2 pL = f.loc(UV, float2(0.47083, 0.92957), float2(-0.000347, -0.0012382), float2(-0.0012792, 0.0003899), 3.3);    // altimeter
float2 pV = f.loc(UV, float2(0.23511, 0.9021), float2(-0.0003733, -0.0012889), float2(-0.0012627, 0.0003009), 2.45);   // vertical speed
float2 pW = f.loc(UV, float2(0.25488, 0.75989), float2(-0.0013622, 0.0000634), float2(0.0000564, 0.001308), 1.0);      // twin (cm)
float2 pG = (pW - float2(0.0, 1.78)) / 1.62, pQ = (pW + float2(0.0, 1.78)) / 1.62;                                     // G (top), AoA (bottom)
// fuel counter: right = -v, up = -u, half size 5.62 x 1.47 cm
float2 pC = float2(-(UV.y - 0.407532) / 0.0074463, -(UV.x - 0.15863) / 0.001953);
float2 dA = ddx(pA), eA = ddy(pA), dT = ddx(pT), eT = ddy(pT), dH = ddx(pH), eH = ddy(pH), dL = ddx(pL), eL = ddy(pL);
float2 dV = ddx(pV), eV = ddy(pV), dG = ddx(pG), eG = ddy(pG), dQ = ddx(pQ), eQ = ddy(pQ), dC = ddx(pC), eC = ddy(pC);

// ---- airspeed 0-800 kt, 300 deg sweep
if (length(pA) < RB) {
  float aa = max(length(dA) + length(eA), 1e-4) * 0.7, w = 0.018; float ink = 0.0;
  for (int i = 0; i <= 16; i++) {
    float2 dd = f.dirc(radians(-150.0 + i * 18.75));
    ink = max(ink, f.ln(f.seg(pA, dd * ((i % 2 == 0) ? 0.74 : 0.82), dd * 0.93), w, aa));
    if (i % 2 == 0 && i > 0) ink = max(ink, f.num(Font, FontSampler, pA, dd * 0.58, 0.24, i / 2, 1, dA, eA));
  }
  float2 nd = f.dirc(radians(-150.0 + clamp(ias, 0.0, 800.0) / 800.0 * 300.0));
  ink = max(ink, f.ln(f.seg(pA, -nd * 0.15, nd * 0.86), 0.03, aa));
  ink = max(ink, f.ln(length(pA), 0.08, aa));
  ink = max(ink, f.chr(Font, FontSampler, pA, float2(-0.09, -0.42), 0.2, 43, dA, eA));
  ink = max(ink, f.chr(Font, FontSampler, pA, float2(0.09, -0.42), 0.2, 52, dA, eA));
  float arc = f.ln(abs(length(pA) - 0.955), 0.025, aa) * step(0.0, atan2(pA.x, pA.y) + radians(150.0 - 150.0 / 800.0 * 300.0)) * step(atan2(pA.x, pA.y), radians(-150.0 + 600.0 / 800.0 * 300.0));
  col = lerp(lerp(FACE, float3(0.1, 0.6, 0.15), arc), INK, ink); glow = ink * 0.05;
}
// ---- attitude: Mirage-style gyro ball (grey-blue sky / black ground, pitch + heading grid), fixed white reference
if (length(pT) < RB) {
  float aa = max(length(dT) + length(eT), 1e-4) * 0.7;
  float rb = 0.93; float2 bp = pT / rb; float zz = sqrt(saturate(1.0 - dot(bp, bp)));
  float3 v = float3(bp.x, bp.y, zz);                                         // point on the ball (z toward the pilot)
  float cr = cos(radians(roll)), sr = sin(radians(roll));
  v = float3(cr * v.x - sr * v.y, sr * v.x + cr * v.y, v.z);                  // undo roll
  float cp = cos(radians(pitch)), sp = sin(radians(pitch));
  v = float3(v.x, cp * v.y - sp * v.z, sp * v.y + cp * v.z);                  // undo pitch
  float lat = degrees(asin(clamp(v.y, -1.0, 1.0)));
  float lon = degrees(atan2(v.x, v.z)) + hdg;
  float pxd = aa * 60.0 / max(zz, 0.2);                                       // grid line width in degrees
  float gl = 1.0 - smoothstep(0.25 * pxd, 0.25 * pxd + pxd, abs(frac(lat / 10.0 + 0.5) - 0.5) * 10.0);
  float gm = (1.0 - smoothstep(0.25 * pxd, 0.25 * pxd + pxd, abs(frac(lon / 30.0 + 0.5) - 0.5) * 30.0)) * step(abs(lat), 80.0);
  float hz = 1.0 - smoothstep(0.6 * pxd, 1.6 * pxd, abs(lat));
  float3 ball = lat > 0.0 ? float3(0.16, 0.22, 0.3) : float3(0.02, 0.02, 0.022);
  float3 grid = lat > 0.0 ? float3(0.75, 0.78, 0.8) : float3(0.62, 0.62, 0.6);
  ball = lerp(ball, grid, max(gl, gm) * 0.85);
  ball = lerp(ball, float3(0.92, 0.92, 0.9), hz);
  ball *= 0.35 + 0.65 * zz;                                                   // limb shading of the sphere
  float onball = 1.0 - smoothstep(rb - 0.02, rb, length(pT));
  float3 colT = lerp(FACE, ball, onball);
  float ink = 0.0;
  for (int j = -3; j <= 3; j++) {                                             // fixed bank scale on the case
    float2 dd = f.dirc(radians(j * (abs(j) == 3 ? 20.0 : 10.0)));
    ink = max(ink, f.ln(f.seg(pT, dd * 0.94, dd * 1.02), 0.014, aa));
  }
  float plane = max(max(f.ln(f.seg(pT, float2(-0.62, 0.0), float2(-0.2, 0.0)), 0.03, aa), f.ln(f.seg(pT, float2(0.2, 0.0), float2(0.62, 0.0)), 0.03, aa)),
                    f.ln(length(pT), 0.045, aa));
  col = lerp(lerp(colT, INK, ink), float3(0.95, 0.5, 0.08), plane); glow = plane * 0.08;
}
// ---- compass card (rotates), fixed aircraft + lubber line
if (length(pH) < RB) {
  float aa = max(length(dH) + length(eH), 1e-4) * 0.7; float ink = 0.0;
  for (int i = 0; i < 36; i++) {
    float2 dd = f.dirc(radians(i * 10.0 - hdg));
    ink = max(ink, f.ln(f.seg(pH, dd * ((i % 3 == 0) ? 0.8 : 0.87), dd * 0.95), 0.014, aa));
  }
  for (int j = 0; j < 12; j++) {
    float a = radians(j * 30.0 - hdg); float2 o = f.dirc(a) * 0.66;
    float2 tp = f.rot(pH - o, a); float2 tdx = f.rot(dH, a), tdy = f.rot(eH, a);
    int c1 = j == 0 ? 46 : j == 3 ? 37 : j == 6 ? 51 : j == 9 ? 55 : -1;
    if (c1 > 0) ink = max(ink, f.chr(Font, FontSampler, tp, float2(0.0, 0.0), 0.24, c1, tdx, tdy));
    else ink = max(ink, f.num(Font, FontSampler, tp, float2(0.0, 0.0), 0.2, j * 3, j * 3 >= 10 ? 2 : 1, tdx, tdy));
  }
  float plane = max(max(f.ln(f.seg(pH, float2(0.0, -0.3), float2(0.0, 0.3)), 0.025, aa), f.ln(f.seg(pH, float2(-0.28, 0.02), float2(0.28, 0.02)), 0.025, aa)),
                    max(f.ln(f.seg(pH, float2(-0.11, -0.26), float2(0.11, -0.26)), 0.022, aa), f.ln(f.seg(pH, float2(0.0, 0.97), float2(0.0, 0.84)), 0.02, aa)));
  col = lerp(lerp(FACE, INK, ink), float3(0.95, 0.45, 0.05), plane); glow = plane * 0.1;
}
// ---- altimeter: 1000 ft per turn + 5-digit window
if (length(pL) < RB) {
  float aa = max(length(dL) + length(eL), 1e-4) * 0.7; float ink = 0.0;
  for (int i = 0; i < 50; i++) {
    float2 dd = f.dirc(radians(i * 7.2));
    ink = max(ink, f.ln(f.seg(pL, dd * ((i % 5 == 0) ? 0.78 : 0.86), dd * 0.95), 0.012, aa));
    if (i % 5 == 0) ink = max(ink, f.num(Font, FontSampler, pL, dd * 0.63, 0.2, i / 5, 1, dL, eL));
  }
  float2 win = abs(pL - float2(0.06, -0.02)) - float2(0.44, 0.14);              // drum counter window (Mirage style)
  float inWin = step(max(win.x, win.y), 0.0);
  float wv = f.num(Font, FontSampler, pL, float2(0.06, -0.02), 0.2, floor(alt / 10.0 + 0.5) * 10.0, 5, dL, eL);
  inWin = max(inWin, f.ln(abs(max(win.x, win.y)), 0.012, aa) * 0.0);
  float2 nd = f.dirc(radians(frac(alt / 1000.0) * 360.0));
  float ndl = max(f.ln(f.seg(pL, -nd * 0.12, nd * 0.88), 0.024, aa), f.ln(length(pL), 0.06, aa));
  col = lerp(lerp(lerp(FACE, INK, ink), float3(0.0, 0.0, 0.0), inWin), INK, max(wv * inWin, ndl)); glow = 0.03 * ink;
}
// ---- vertical speed: 0 at 9 o'clock, +/-6000 ft/min
if (length(pV) < RB) {
  float aa = max(length(dV) + length(eV), 1e-4) * 0.7; float ink = 0.0;
  for (int i = -6; i <= 6; i++) {
    float2 dd = f.dirc(radians(-90.0 + i * 27.0));
    ink = max(ink, f.ln(f.seg(pV, dd * ((i % 2 == 0) ? 0.74 : 0.84), dd * 0.95), 0.014, aa));
    if (i % 2 == 0) ink = max(ink, f.num(Font, FontSampler, pV, dd * 0.56, 0.2, abs(i), 1, dV, eV));
  }
  float2 nd = f.dirc(radians(-90.0 + clamp(vs / 1000.0, -6.3, 6.3) * 27.0));
  ink = max(ink, max(f.ln(f.seg(pV, float2(0.0, 0.0), nd * 0.86), 0.028, aa), f.ln(length(pV), 0.07, aa)));
  col = lerp(FACE, INK, ink); glow = 0.03 * ink;
}
// ---- twin: load factor (-3..+9 g) top, incidence (0..30 deg) bottom
if (length(pG) < 1.0 || length(pQ) < 1.0) {
  bool top = length(pG) < 1.0; float2 p = top ? pG : pQ; float2 dx = top ? dG : dQ, dy = top ? eG : eQ;
  float aa = max(length(dx) + length(dy), 1e-4) * 0.7; float ink = 0.0;
  float lo = top ? -3.0 : 0.0, hi = top ? 9.0 : 30.0, st = top ? 1.0 : 5.0, v = top ? gl : aoa;
  for (int i = 0; i <= 12; i++) {
    float t = lo + i * st; if (t > hi + 0.01) break;
    float2 dd = f.dirc(radians(-135.0 + (t - lo) / (hi - lo) * 270.0));
    ink = max(ink, f.ln(f.seg(p, dd * 0.78, dd * 0.95), 0.02, aa));
  }
  ink = max(ink, f.chr(Font, FontSampler, p, float2(0.0, -0.45), 0.32, top ? 39 : 32, dx, dy));
  float2 nd = f.dirc(radians(-135.0 + clamp((v - lo) / (hi - lo), 0.0, 1.0) * 270.0));
  ink = max(ink, max(f.ln(f.seg(p, float2(0.0, 0.0), nd * 0.85), 0.04, aa), f.ln(length(p), 0.1, aa)));
  col = lerp(FACE, INK, ink); glow = 0.03 * ink;
}
// ---- fuel quantity counter (kg), rolling last drum
if (abs(pC.x) < 1.0 && abs(pC.y) < 1.0) {
  float cw = 2.0 / 6.0; int k = (int)floor((pC.x + 1.0) / cw);
  float cx = (pC.x + 1.0 - (k + 0.5) * cw) * 5.62;     // cm from drum centre
  float cy = pC.y * 1.47;
  float place = floor(pow(10.0, 5 - k) + 0.5);
  float v = fuel / place; float dg = floor(v - 10.0 * floor(v / 10.0) + 0.001);
  float rl = (k == 5) ? frac(fuel) : saturate((frac(fuel / place) * place - (place - 1.0)));   // carry rolls the next drum
  float H = 2.2, sp = 2.6; float ink = 0.0;
  float2 dx = float2(ddx(pC.x) * 5.62, ddx(pC.y) * 1.47) / H, dy = float2(ddy(pC.x) * 5.62, ddy(pC.y) * 1.47) / H;
  float yy = cy + rl * sp;
  ink = max(ink, f.glyph(Font, FontSampler, float2(cx / H + 0.5, yy / H + 0.5), 16 + (int)dg, dx, dy));
  ink = max(ink, f.glyph(Font, FontSampler, float2(cx / H + 0.5, (yy - sp) / H + 0.5), 16 + (int)fmod(dg + 1.0, 10.0), dx, dy));
  float edge = smoothstep(0.75, 1.0, abs(pC.y));
  col = lerp(float3(0.015, 0.015, 0.015), float3(0.9, 0.9, 0.88), ink) * (1.0 - 0.7 * edge);
}
// bezel ring for every round dial
float rr = min(min(min(length(pA), length(pT)), min(length(pH), length(pL))), length(pV));
if (rr >= 1.0 && rr < RB) { col = BEZ; glow = 0.0; }
return float4(col, glow);
"""

MASK = r"""
// x: gauge glass (glossy cover), y: self-lit display glow
float2 r = float2(0.0, 0.0);
float2 C[6] = { float2(0.79321, 0.51917), float2(0.44446, 0.92664), float2(0.47083, 0.91321), float2(0.47083, 0.92957), float2(0.23511, 0.9021), float2(0.25488, 0.75989) };
float  Rr[6] = { 0.0034, 0.0031, 0.0045, 0.0044, 0.0034, 0.0045 };
for (int i = 0; i < 6; i++) r.x = max(r.x, 1.0 - smoothstep(Rr[i] * 0.9, Rr[i], length(UV - C[i])));
// display islands (pixel boxes in the 8192 atlas): centre MFD, BOOM/G digital, caution lights, clock, engine display
float4 B[6] = { float4(3610, 4936, 146, 148), float4(1324, 1963, 38, 70), float4(1160, 1953, 38, 70), float4(180, 3677, 40, 95), float4(426, 3868, 38, 96), float4(6752, 6868, 86, 85) };
float px = UV.x * 8192.0, py = UV.y * 8192.0;
for (int j = 0; j < 6; j++) {
  float4 b = B[j]; float inb = step(b.x + 5.0, px) * step(px, b.x + b.z - 5.0) * step(b.y + 5.0, py) * step(py, b.y + b.w - 5.0);
  r.y = max(r.y, inb);
}
return r;
"""

created = False
if not eal.does_asset_exist(DST):
    eal.duplicate_asset(SRC, DST); created = True
m = eal.load_asset(DST)
hud = "/Game/AirRefueler/Sim/HUD"
mpc = eal.load_asset(hud + "/MPC_HUD")
E = lambda cls, x, y: mel.create_material_expression(m, cls, x, y)
def find(name):
    return unreal.find_object(None, m.get_path_name() + ":" + name)
live = find("PanelLiveNode"); mask = find("PanelMaskNode")
if created or live is None:
    base = mel.get_material_property_input_node(m, unreal.MaterialProperty.MP_BASE_COLOR)
    rough = mel.get_material_property_input_node(m, unreal.MaterialProperty.MP_ROUGHNESS)
    uv = E(unreal.MaterialExpressionTextureCoordinate, -2200, 1400)
    live = E(unreal.MaterialExpressionCustom, -1500, 1400); live.rename("PanelLiveNode")
    mask = E(unreal.MaterialExpressionCustom, -1500, 1800); mask.rename("PanelMaskNode")
    for node, ins, outt in ((live, ["UV", "Base", "Font", "AF", "AU", "Vel", "D0", "D1", "D2"], unreal.CustomMaterialOutputType.CMOT_FLOAT4),
                            (mask, ["UV"], unreal.CustomMaterialOutputType.CMOT_FLOAT2)):
        lst = []
        for n in ins:
            ci = unreal.CustomInput(); ci.set_editor_property("input_name", n); lst.append(ci)
        node.set_editor_property("inputs", lst); node.set_editor_property("output_type", outt)
    def coll(name, y):
        e = E(unreal.MaterialExpressionCollectionParameter, -2200, y); e.set_editor_property("collection", mpc); e.set_editor_property("parameter_name", name); return e
    font = E(unreal.MaterialExpressionTextureObject, -2200, 1500); font.set_editor_property("texture", eal.load_asset(hud + "/T_HUDFont"))
    mel.connect_material_expressions(uv, "", live, "UV"); mel.connect_material_expressions(uv, "", mask, "UV")
    mel.connect_material_expressions(base, "", live, "Base"); mel.connect_material_expressions(font, "", live, "Font")
    for i, n in enumerate(["AFwd", "AUp", "Vel", "D0", "D1", "D2"]):
        mel.connect_material_expressions(coll(n, 1600 + i * 80), "", live, ["AF", "AU", "Vel", "D0", "D1", "D2"][i])
    rgb = E(unreal.MaterialExpressionComponentMask, -1200, 1400)
    for c, v in zip("rgba", (True, True, True, False)): rgb.set_editor_property(c, v)
    ga = E(unreal.MaterialExpressionComponentMask, -1200, 1500)
    for c, v in zip("rgba", (False, False, False, True)): ga.set_editor_property(c, v)
    mel.connect_material_expressions(live, "", rgb, ""); mel.connect_material_expressions(live, "", ga, "")
    mx = E(unreal.MaterialExpressionComponentMask, -1200, 1800)
    for c, v in zip("rgba", (True, False, False, False)): mx.set_editor_property(c, v)
    my = E(unreal.MaterialExpressionComponentMask, -1200, 1900)
    for c, v in zip("rgba", (False, True, False, False)): my.set_editor_property(c, v)
    mel.connect_material_expressions(mask, "", mx, ""); mel.connect_material_expressions(mask, "", my, "")
    # emissive = colour * (display glow * DisplayGlow + gauge ink glow * GaugeBacklight)
    dg = E(unreal.MaterialExpressionScalarParameter, -1200, 2000); dg.set_editor_property("parameter_name", "DisplayGlow"); dg.set_editor_property("default_value", 1500.0)
    gb = E(unreal.MaterialExpressionScalarParameter, -1200, 2100); gb.set_editor_property("parameter_name", "GaugeBacklight"); gb.set_editor_property("default_value", 2000.0)
    m1 = E(unreal.MaterialExpressionMultiply, -1000, 1950); mel.connect_material_expressions(my, "", m1, "A"); mel.connect_material_expressions(dg, "", m1, "B")
    m2 = E(unreal.MaterialExpressionMultiply, -1000, 2050); mel.connect_material_expressions(ga, "", m2, "A"); mel.connect_material_expressions(gb, "", m2, "B")
    ad = E(unreal.MaterialExpressionAdd, -850, 2000); mel.connect_material_expressions(m1, "", ad, "A"); mel.connect_material_expressions(m2, "", ad, "B")
    em = E(unreal.MaterialExpressionMultiply, -700, 1700); mel.connect_material_expressions(rgb, "", em, "A"); mel.connect_material_expressions(ad, "", em, "B")
    mel.connect_material_property(rgb, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(em, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    # glossy gauge glass, satin displays
    gr = E(unreal.MaterialExpressionScalarParameter, -1000, 2200); gr.set_editor_property("parameter_name", "GlassRoughness"); gr.set_editor_property("default_value", 0.08)
    lr = E(unreal.MaterialExpressionLinearInterpolate, -700, 2200)
    mel.connect_material_expressions(rough, "", lr, "A"); mel.connect_material_expressions(gr, "", lr, "B"); mel.connect_material_expressions(mx, "", lr, "Alpha")
    mel.connect_material_property(lr, "", unreal.MaterialProperty.MP_ROUGHNESS)
    log("graph built")
live.set_editor_property("code", LIVE); live.set_editor_property("description", "PanelLive")
mask.set_editor_property("code", MASK); mask.set_editor_property("description", "PanelMask")
mel.recompile_material(m); eal.save_loaded_asset(m)
mi = eal.load_asset(MAT + "/MI_Salon_VRay1_Cutout")
if mi.get_editor_property("parent") != m:
    mi.set_editor_property("parent", m)
mel.set_material_instance_scalar_parameter_value(mi, "GaugeBacklight", 400.0)   # faint lit markings
mel.set_material_instance_scalar_parameter_value(mi, "DisplayGlow", 1500.0)
mel.update_material_instance(mi); eal.save_loaded_asset(mi)
log("done (created=%s)" % created)
