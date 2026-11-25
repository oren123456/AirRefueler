"""Cumulus puffs at the formation's altitude that stream past at the flight speed (BP_CloudStream moves them; some
spawn on the formation's track so you fly through them). M_CloudPuff: raymarched density inside a sphere (fbm-
shaped, flat-ish base, sun-side lighting), back faces only, no depth test, clipped by scene depth. Re-runnable."""
import unreal, random
D = "/Game/AirRefueler/Sim/Clouds"
eal = unreal.EditorAssetLibrary; at = unreal.AssetToolsHelpers.get_asset_tools(); mel = unreal.MaterialEditingLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
log = lambda s: unreal.log("[Puffs] " + s)
N_PUFFS = 14

CODE = r"""
struct CP {
  float h(float3 p) { p = frac(p * 0.1031); p += dot(p, p.zyx + 31.32); return frac((p.x + p.y) * p.z); }
  float n3(float3 p) { float3 i = floor(p), f = frac(p); f = f * f * (3.0 - 2.0 * f);
    return lerp(lerp(lerp(h(i), h(i + float3(1, 0, 0)), f.x), lerp(h(i + float3(0, 1, 0)), h(i + float3(1, 1, 0)), f.x), f.y),
                lerp(lerp(h(i + float3(0, 0, 1)), h(i + float3(1, 0, 1)), f.x), lerp(h(i + float3(0, 1, 1)), h(i + float3(1, 1, 1)), f.x), f.y), f.z); }
  float fbm(float3 p) { return 0.5 * n3(p) + 0.27 * n3(p * 2.07 + 7.3) + 0.15 * n3(p * 4.31 + 1.7) + 0.08 * n3(p * 8.9 + 3.1); }
};
if (TS > 0.0) return float4(0, 0, 0, 0);            // back faces only (works from outside and inside the sphere)
CP c;
float3 rd = normalize(WP - Cam); float3 oc = Cam - C;
float b = dot(oc, rd), cc = dot(oc, oc) - R * R, hh = b * b - cc;
if (hh <= 0.0) return float4(0, 0, 0, 0);
hh = sqrt(hh); float t0 = max(-b - hh, 0.0), t1 = -b + hh;
t1 = min(t1, SD / max(dot(rd, CF), 1e-3));          // stop at opaque geometry (aircraft, cockpit)
if (t1 <= t0) return float4(0, 0, 0, 0);
float seed = c.h(floor(C / 997.0));
float jit = frac(sin(dot(rd, float3(12.9898, 78.233, 45.164)) * 43758.5453));
const int N = 22; float dt = (t1 - t0) / N; float Tr = 1.0; float3 acc = float3(0, 0, 0);
for (int i = 0; i < N; i++) {
  float3 p = Cam + rd * (t0 + (i + jit) * dt);
  float3 q = (p - C) / R;
  float r = length(q * float3(1.0, 1.0, 1.45) + float3(0.0, 0.0, 0.12));
  float n = c.fbm(p / (R * 0.42) + seed * 57.0 + float3(0.0, 0.0, Time * 0.015));
  // billowy lobes + eroded wispy edges, flat-ish base
  float d = saturate((1.0 - r) * 2.0 + (n - 0.52) * 2.6) * smoothstep(-0.66, -0.5, q.z);
  if (d > 0.002) {
    float ext = d * Sigma * dt;
    float lit = saturate(0.3 + 0.7 * (dot(normalize(q + 1e-4), L) * 0.5 + 0.5)) * (0.75 + 0.25 * saturate(q.z + 0.5));
    float3 col = Amb + Sun * lit;
    float a = 1.0 - exp(-ext);
    acc += Tr * a * col; Tr *= 1.0 - a;
    if (Tr < 0.01) break;
  }
}
return float4(acc / max(1.0 - Tr, 1e-4), 1.0 - Tr);
"""

mp = D + "/M_CloudPuff"
if eal.does_asset_exist(mp):
    m = eal.load_asset(mp); mel.delete_all_material_expressions(m)
else:
    m = at.create_asset("M_CloudPuff", D, unreal.Material, unreal.MaterialFactoryNew())
m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
m.set_editor_property("two_sided", True)
m.set_editor_property("disable_depth_test", True)
E = lambda cls, x, y: mel.create_material_expression(m, cls, x, y)
def par(cls, name, val, y):
    e = E(cls, -1000, y); e.set_editor_property("parameter_name", name); e.set_editor_property("default_value", val); return e
cf = E(unreal.MaterialExpressionTransform, -1000, 300)
cf.set_editor_property("transform_source_type", unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_VIEW)
cf.set_editor_property("transform_type", unreal.MaterialVectorCoordTransform.TRANSFORM_WORLD)
fwd = E(unreal.MaterialExpressionConstant3Vector, -1200, 300); fwd.set_editor_property("constant", unreal.LinearColor(0, 0, 1, 0))
mel.connect_material_expressions(fwd, "", cf, "")
src = {"WP": E(unreal.MaterialExpressionWorldPosition, -1000, -200), "Cam": E(unreal.MaterialExpressionCameraPositionWS, -1000, -100),
       "C": E(unreal.MaterialExpressionObjectPositionWS, -1000, 0), "R": E(unreal.MaterialExpressionObjectRadius, -1000, 100),
       "SD": E(unreal.MaterialExpressionSceneDepth, -1000, 200), "CF": cf,
       "L": E(unreal.MaterialExpressionSkyAtmosphereLightDirection, -1000, 400), "TS": E(unreal.MaterialExpressionTwoSidedSign, -1000, 500),
       "Time": E(unreal.MaterialExpressionTime, -1000, 600),
       "Sun": par(unreal.MaterialExpressionVectorParameter, "SunLum", unreal.LinearColor(2600, 2500, 2350, 1), 700),
       "Amb": par(unreal.MaterialExpressionVectorParameter, "AmbientLum", unreal.LinearColor(700, 780, 950, 1), 800),
       "Sigma": par(unreal.MaterialExpressionScalarParameter, "Sigma", 0.00035, 900)}
cu = E(unreal.MaterialExpressionCustom, -500, 200)
cu.set_editor_property("code", CODE); cu.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT4); cu.set_editor_property("description", "CloudPuff")
ins = []
for n in src:
    ci = unreal.CustomInput(); ci.set_editor_property("input_name", n); ins.append(ci)
cu.set_editor_property("inputs", ins)
for n, e in src.items(): mel.connect_material_expressions(e, "", cu, n)
rgb = E(unreal.MaterialExpressionComponentMask, -250, 150)
for ch, v in zip("rgba", (True, True, True, False)): rgb.set_editor_property(ch, v)
al = E(unreal.MaterialExpressionComponentMask, -250, 300)
for ch, v in zip("rgba", (False, False, False, True)): al.set_editor_property(ch, v)
mel.connect_material_expressions(cu, "", rgb, ""); mel.connect_material_expressions(cu, "", al, "")
mel.connect_material_property(rgb, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
mel.connect_material_property(al, "", unreal.MaterialProperty.MP_OPACITY)
mel.recompile_material(m); eal.save_loaded_asset(m)
log("material compiled")

import sys
if len(sys.argv) > 1 and sys.argv[1] == "mat":
    raise SystemExit
bp_path = D + "/BP_CloudStream"
if not eal.does_asset_exist(bp_path):
    f = unreal.BlueprintFactory(); f.set_editor_property("parent_class", unreal.Actor)
    at.create_asset("BP_CloudStream", D, unreal.Blueprint, f)
bp = eal.load_asset(bp_path)

pawn = next(a for a in eas.get_all_level_actors() if a.get_class().get_name().startswith("BP_MiragePawn"))
pl = pawn.get_actor_location()
for a in eas.get_all_level_actors():
    if a.actor_has_tag("CloudPuff") or a.get_actor_label() == "CloudStream": eas.destroy_actor(a)
sphere = eal.load_asset("/Engine/BasicShapes/Sphere")
random.seed(7)
for i in range(N_PUFFS):
    sc = random.uniform(250.0, 700.0)    # sphere mesh radius 50 cm -> 125..350 m
    loc = unreal.Vector(pl.x + random.uniform(-80000, 80000), pl.y + random.uniform(250000, 1500000), pl.z + random.uniform(-25000, 25000))
    a = eas.spawn_actor_from_class(unreal.StaticMeshActor, loc)
    a.set_actor_label("CloudPuff_%02d" % i); a.tags = [unreal.Name("CloudPuff")]
    smc = a.static_mesh_component; smc.set_mobility(unreal.ComponentMobility.MOVABLE)
    smc.set_static_mesh(sphere); smc.set_material(0, m)
    smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION); smc.set_editor_property("cast_shadow", False)
    a.set_actor_scale3d(unreal.Vector(sc, sc, sc * 0.75))
    a.set_folder_path("Clouds")
cs = eas.spawn_actor_from_class(bp.generated_class(), pl); cs.set_actor_label("CloudStream"); cs.set_folder_path("Clouds")
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
log("done: %d puffs" % N_PUFFS)
