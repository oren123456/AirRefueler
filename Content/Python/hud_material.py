"""HUD step 2: M_HUD on the Mirage combiner (Mirage_HUDGlass). Collimated: every pixel's view direction is converted
to angles in the aircraft frame (MPC_HUD AFwd/AUp), symbology is drawn in those angles -> it sits at infinity and is
only visible through the glass. Pitch ladder/horizon are world-referenced (conformal). Data from BP_HUDDriver via
MPC_HUD. Also lowers the PilotCam 4 cm so the design eye looks through the combiner. Re-runnable."""
import unreal
HUD = "/Game/AirRefueler/Sim/HUD"
eal = unreal.EditorAssetLibrary; at = unreal.AssetToolsHelpers.get_asset_tools(); mel = unreal.MaterialEditingLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
log = lambda s: unreal.log("[HUD] " + s)

CODE = r"""
struct HF {
  float seg(float2 p, float2 a, float2 b) { float2 pa = p - a, ba = b - a; float h = saturate(dot(pa, ba) / dot(ba, ba)); return length(pa - ba * h); }
  float ln(float d, float w, float aa) { return 1.0 - smoothstep(w, w + aa, d); }
  float box(float2 q, float2 hb, float w, float aa) { float2 e = abs(q) - hb; float d = length(max(e, 0.0)) + min(max(e.x, e.y), 0.0); return ln(abs(d), w, aa); }
  float glyph(Texture2D T, SamplerState S, float2 uv, int c, float2 dx, float2 dy) {
    if (c <= 0 || uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) return 0.0;
    float2 t = (float2(c % 8, c / 8) + float2(uv.x, 1.0 - uv.y)) / 8.0;
    return T.SampleGrad(S, t, float2(dx.x, -dx.y) / 8.0, float2(dy.x, -dy.y) / 8.0).r;
  }
  int wc(int w, int i) {
    int W[96] = { 51,52,47,55,37,36,-1,-1,  52,50,33,41,44,-1,-1,-1,  50,37,33,36,57,-1,-1,-1,  35,47,46,52,33,35,52,-1,
                  50,37,55,41,46,36,-1,-1,  50,46,39,-1,-1,-1,-1,-1,  35,44,51,-1,-1,-1,-1,-1,  38,53,37,44,-1,-1,-1,-1,
                  43,39,-1,-1,-1,-1,-1,-1,  38,44,47,55,-1,-1,-1,-1,  45,-1,-1,-1,-1,-1,-1,-1,  39,-1,-1,-1,-1,-1,-1,-1 };
    return (i < 0 || i > 7) ? -1 : W[w * 8 + i];
  }
  int wlen(int w) { int L[12] = { 6, 5, 5, 7, 6, 3, 3, 4, 2, 4, 1, 1 }; return L[w]; }
  // word w with its left edge at o.x, vertical centre o.y, cell height hc
  float word(Texture2D T, SamplerState S, float2 p, float2 o, float hc, int w, float2 dx, float2 dy) {
    float adv = 0.45 * hc; float2 q = p - o; int k = (int)floor(q.x / adv);
    if (k < 0 || k > 7) return 0.0;
    int c = wc(w, k); if (c < 0) return 0.0;
    return glyph(T, S, float2((q.x - (k + 0.5) * adv) / hc + 0.5, q.y / hc + 0.5), c, dx / hc, dy / hc);
  }
  // number in n character slots, right aligned, dec decimals, sg: sign in slot 0, zp: leading zeros
  float num(Texture2D T, SamplerState S, float2 p, float2 o, float hc, float v, int n, int dec, int sg, int zp, float2 dx, float2 dy) {
    float adv = 0.45 * hc; float2 q = p - o; int k = (int)floor(q.x / adv);
    if (k < 0 || k >= n) return 0.0;
    int c = 0;
    if (sg == 1 && k == 0) c = v < 0.0 ? 13 : 11;
    else {
      int r = n - 1 - k;
      float iv = floor(abs(v) * pow(10.0, dec) + 0.5);
      if (dec > 0 && r == dec) c = 14;
      else {
        int dp = (dec > 0 && r > dec) ? r - 1 : r;
        float place = floor(pow(10.0, dp) + 0.5);
        bool lead = (iv < place - 0.5) && (dp > dec);
        float qd = floor(iv / place + 0.01);                       // GPU division/fmod are approximate:
        int dg = (int)(qd - 10.0 * floor(qd / 10.0 + 0.01) + 0.5);  // round, never truncate (8 -> 7.9999 -> 7)
        if (!lead || zp == 1) c = 16 + clamp(dg, 0, 9);
      }
    }
    return glyph(T, S, float2((q.x - (k + 0.5) * adv) / hc + 0.5, q.y / hc + 0.5), c, dx / hc, dy / hc);
  }
};
HF f;
float3 F = normalize(AF.xyz);
float3 R = normalize(cross(AU.xyz, F));
float3 U = cross(F, R);
float3 d = normalize(WP - Cam);
float df = dot(d, F);
float2 p = degrees(float2(atan2(dot(d, R), df), atan2(dot(d, U), df)));
float2 dx = ddx(p), dy = ddy(p);
float aa = max(max(length(float2(dx.x, dy.x)), length(float2(dx.y, dy.y))), 1e-4);
float w = max(0.025, 0.45 * aa);
float HC = 0.62; float ADV = 0.45 * HC;
float s = 0.0;

// ---- flight path marker (air-mass velocity = nose * TAS + motion relative to the tanker)
float3 vd = normalize(F * 19800.0 + Vel.xyz);
float vf = dot(vd, F);
float2 fp = degrees(float2(atan2(dot(vd, R), vf), atan2(dot(vd, U), vf)));
float2 q = p - fp;
s = max(s, f.ln(abs(length(q) - 0.26), w, aa));
s = max(s, f.ln(f.seg(q, float2(-0.75, 0.0), float2(-0.26, 0.0)), w, aa));
s = max(s, f.ln(f.seg(q, float2(0.26, 0.0), float2(0.75, 0.0)), w, aa));
s = max(s, f.ln(f.seg(q, float2(0.0, 0.26), float2(0.0, 0.52)), w, aa));

// ---- horizon + pitch ladder (world referenced)
float3 Fh = normalize(float3(F.x, F.y, 0.0) + float3(1e-5, 0, 0));
float3 Rh = normalize(cross(float3(0, 0, 1), Fh));
float elw = degrees(asin(clamp(d.z, -1.0, 1.0)));
float azw = degrees(atan2(dot(d, Rh), dot(d, Fh)));
float2 L = float2(azw, elw);
float2 ldx = ddx(L), ldy = ddy(L);
float A = abs(azw);
s = max(s, f.ln(abs(elw), w, aa) * step(1.0, A) * step(A, 6.0));
for (int k = -3; k <= 3; k++) {
  if (k == 0) continue;
  float P = k * 5.0;
  float dv = elw - P;
  float on = step(1.0, A) * step(A, 2.3);
  if (k < 0) on *= step(frac((A - 1.0) / 0.42), 0.6);
  s = max(s, f.ln(abs(dv), w, aa) * on);
  float tdv = -sign(P) * dv;
  s = max(s, f.ln(abs(A - 2.3), w, aa) * step(0.0, tdv) * step(tdv, 0.3));
  s = max(s, f.num(Font, FontSampler, L, float2(2.45, P), HC * 0.8, abs(P), 2, 0, 0, 0, ldx, ldy));
  s = max(s, f.num(Font, FontSampler, L, float2(-2.45 - 2.0 * 0.45 * HC * 0.8, P), HC * 0.8, abs(P), 2, 0, 0, 0, ldx, ldy));
}

// ---- heading tape (top)
float hdg = degrees(atan2(Fh.y, Fh.x)); hdg = hdg < 0.0 ? hdg + 360.0 : hdg;
float ty = 2.6, sc = 0.3;
float h0 = floor((hdg - 15.0) / 5.0) * 5.0;
for (int i = 0; i < 7; i++) {
  float hh = h0 + i * 5.0;
  float x = (hh - hdg) * sc;
  float inw = step(abs(x), 4.0);
  bool major = abs(fmod(hh + 3600.0, 10.0)) < 0.5;
  s = max(s, f.ln(f.seg(p, float2(x, ty), float2(x, ty + (major ? 0.32 : 0.18))), w, aa) * inw);
  if (major) s = max(s, f.num(Font, FontSampler, p, float2(x - ADV, ty + 0.72), HC, fmod(hh / 10.0 + 36.0, 36.0), 2, 0, 0, 1, dx, dy) * inw);
}
s = max(s, f.ln(f.seg(p, float2(0.0, ty - 0.04), float2(-0.16, ty - 0.3)), w, aa));
s = max(s, f.ln(f.seg(p, float2(0.0, ty - 0.04), float2(0.16, ty - 0.3)), w, aa));

// ---- speed (left) / altitude (right) boxes, Mach, G
float ias = D0.x;
s = max(s, f.num(Font, FontSampler, p, float2(-3.55 - 1.5 * ADV, -1.6), HC, ias, 3, 0, 0, 0, dx, dy));
s = max(s, f.box(p - float2(-3.55, -1.6), float2(1.5 * ADV + 0.12, 0.5 * HC), w, aa));
s = max(s, f.word(Font, FontSampler, p, float2(-4.25, -2.5), HC * 0.85, 10, dx, dy));
s = max(s, f.num(Font, FontSampler, p, float2(-4.25 + 1.6 * ADV, -2.5), HC * 0.85, ias / 456.0, 4, 2, 0, 0, dx, dy));
s = max(s, f.word(Font, FontSampler, p, float2(-4.25, -3.3), HC * 0.85, 11, dx, dy));
s = max(s, f.num(Font, FontSampler, p, float2(-4.25 + 1.6 * ADV, -3.3), HC * 0.85, D0.z, 3, 1, 0, 0, dx, dy));
float alt = floor(D0.y / 10.0 + 0.5) * 10.0;
s = max(s, f.num(Font, FontSampler, p, float2(3.35 - 2.5 * ADV, -1.6), HC, alt, 5, 0, 0, 0, dx, dy));
s = max(s, f.box(p - float2(3.35, -1.6), float2(2.5 * ADV + 0.12, 0.5 * HC), w, aa));

// ---- refuelling block (bottom)
int st = (int)(D0.w + 0.5);
int sw = st == 0 ? 0 : st == 1 ? 1 : st == 2 ? 2 : st == 3 ? (D1.w > 0.5 ? 9 : 3) : 4;
float blink = (st == 3 && D1.w < 0.5) ? step(0.3, frac(Time * 1.5)) : 1.0;
s = max(s, f.word(Font, FontSampler, p, float2(-0.5 * f.wlen(sw) * ADV * 1.1, -6.6), HC * 1.1, sw, dx, dy) * blink);
s = max(s, f.word(Font, FontSampler, p, float2(-4.3, -7.6), HC, 5, dx, dy));
s = max(s, f.num(Font, FontSampler, p, float2(-4.3 + 3.6 * ADV, -7.6), HC, min(D1.y, 99.9), 4, 1, 0, 0, dx, dy));
s = max(s, f.word(Font, FontSampler, p, float2(0.95, -7.6), HC, 6, dx, dy));
s = max(s, f.num(Font, FontSampler, p, float2(0.95 + 3.6 * ADV, -7.6), HC, clamp(D1.x, -9.9, 9.9), 4, 1, 1, 0, dx, dy));
s = max(s, f.word(Font, FontSampler, p, float2(-2.3, -8.6), HC, 7, dx, dy));
s = max(s, f.num(Font, FontSampler, p, float2(-2.3 + 4.6 * ADV, -8.6), HC, D1.z, 4, 0, 0, 0, dx, dy));
s = max(s, f.word(Font, FontSampler, p, float2(-2.3 + 9.0 * ADV, -8.6), HC, 8, dx, dy));
return saturate(s) * step(0.0, df);
"""

mp = HUD + "/M_HUD"
if eal.does_asset_exist(mp):
    m = eal.load_asset(mp); mel.delete_all_material_expressions(m)   # never delete an in-use material (crashes)
else:
    m = at.create_asset("M_HUD", HUD, unreal.Material, unreal.MaterialFactoryNew())
m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
m.set_editor_property("two_sided", True)
m.set_editor_property("translucency_pass", unreal.MaterialTranslucencyPass.MTP_AFTER_DOF)
E = lambda cls, x, y: mel.create_material_expression(m, cls, x, y)
mpc = eal.load_asset(HUD + "/MPC_HUD")
def coll(name, y):
    e = E(unreal.MaterialExpressionCollectionParameter, -1100, y)
    e.set_editor_property("collection", mpc); e.set_editor_property("parameter_name", name); return e
def param(cls, name, val, x, y):
    e = E(cls, x, y); e.set_editor_property("parameter_name", name); e.set_editor_property("default_value", val); return e
src = {"WP": E(unreal.MaterialExpressionWorldPosition, -1100, -300), "Cam": E(unreal.MaterialExpressionCameraPositionWS, -1100, -200),
       "AF": coll("AFwd", -100), "AU": coll("AUp", 0), "Vel": coll("Vel", 100), "D0": coll("D0", 200), "D1": coll("D1", 300),
       "Time": E(unreal.MaterialExpressionTime, -1100, 400)}
font = E(unreal.MaterialExpressionTextureObject, -1100, 500); font.set_editor_property("texture", eal.load_asset(HUD + "/T_HUDFont"))
src["Font"] = font
cu = E(unreal.MaterialExpressionCustom, -600, 0)
cu.set_editor_property("code", CODE); cu.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT1)
cu.set_editor_property("description", "CollimatedHUD")
ins = []
for n in src:
    ci = unreal.CustomInput(); ci.set_editor_property("input_name", n); ins.append(ci)
cu.set_editor_property("inputs", ins)
for n, e in src.items():
    mel.connect_material_expressions(e, "", cu, n)
col = param(unreal.MaterialExpressionVectorParameter, "HudColor", unreal.LinearColor(0.10, 1.0, 0.22, 1), -600, 250)
bri = param(unreal.MaterialExpressionScalarParameter, "Brightness", 6000.0,   # cd/m2-ish: the scene uses physical light units (sun 12000 lux)
                -600, 400)
tint = param(unreal.MaterialExpressionVectorParameter, "GlassTint", unreal.LinearColor(0.10, 0.11, 0.08, 1), -600, 550)
gop = param(unreal.MaterialExpressionScalarParameter, "GlassOpacity", 0.08, -600, 700)
mul = E(unreal.MaterialExpressionMultiply, -350, 300); mel.connect_material_expressions(col, "", mul, "A"); mel.connect_material_expressions(bri, "", mul, "B")
lerp = E(unreal.MaterialExpressionLinearInterpolate, -150, 200)
mel.connect_material_expressions(tint, "", lerp, "A"); mel.connect_material_expressions(mul, "", lerp, "B"); mel.connect_material_expressions(cu, "", lerp, "Alpha")
op = E(unreal.MaterialExpressionLinearInterpolate, -150, 500)
mel.connect_material_expressions(gop, "", op, "A"); op.set_editor_property("const_b", 1.0); mel.connect_material_expressions(cu, "", op, "Alpha")
mel.connect_material_property(lerp, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
mel.connect_material_property(op, "", unreal.MaterialProperty.MP_OPACITY)
mel.recompile_material(m); eal.save_loaded_asset(m)
log("M_HUD compiled")

for a in eas.get_all_level_actors():
    if a.get_actor_label() == "Mirage_HUDGlass":
        smc = a.static_mesh_component; smc.modify()
        for i in range(smc.get_num_materials()): smc.set_material(i, m)
        log("combiner material set (%d slots)" % smc.get_num_materials())

# design eye: PilotCam 4 cm lower so the line of sight passes through the upper part of the combiner
bp = eal.load_asset("/Game/AirRefueler/Sim/BP_MiragePawn")
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem); SDL = unreal.SubobjectDataBlueprintFunctionLibrary
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    o = SDL.get_object(SDL.get_data(h))
    if o and o.get_name().startswith("PilotCam"):
        rl = o.get_editor_property("relative_location")
        if abs(rl.z - (-3.0)) < 0.01:          # original eye height -> 4 cm lower (only once)
            o.set_editor_property("relative_location", unreal.Vector(rl.x, rl.y, -7.0))
            unreal.BlueprintEditorLibrary.compile_blueprint(bp); eal.save_loaded_asset(bp)
        log("PilotCam rel %s" % o.get_editor_property("relative_location"))
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
log("done")
