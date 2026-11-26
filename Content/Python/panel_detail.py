"""Cockpit surface realism on M_MayaPBR_Live: paint grain (detail normal), satin roughness with smudges/
fingerprints, subtle tone mottling, glossy display glass; all procedural in atlas-UV space (~10.8 atlas px per cm),
faded with screen footprint so it never shimmers. Also re-parents MI_Salon_VRay1 (rest of the cockpit) to the
live material. Re-runnable: updates the Custom node code in place."""
import unreal
MAT = "/Game/AirRefueler/Models/Aircraft/Mirage/Materials"; DST = MAT + "/M_MayaPBR_Live"
eal = unreal.EditorAssetLibrary; mel = unreal.MaterialEditingLibrary
log = lambda s: unreal.log("[PanelDetail] " + s)
DETAIL = r"""
struct DF {
  float h(float2 p) { float3 p3 = frac(float3(p.xyx) * 0.1031); p3 += dot(p3, p3.yzx + 33.33); return frac((p3.x + p3.y) * p3.z); }
  float vn(float2 p) { float2 i = floor(p), f = frac(p); f = f * f * (3.0 - 2.0 * f);
    return lerp(lerp(h(i), h(i + float2(1, 0)), f.x), lerp(h(i + float2(0, 1)), h(i + float2(1, 1)), f.x), f.y); }
  // rotated octaves hide the value-noise lattice: ~4 mm orange peel + ~1.5 mm grain
  float grain(float2 p) {
    float2 q = float2(0.8 * p.x - 0.6 * p.y, 0.6 * p.x + 0.8 * p.y), r = float2(0.28 * p.x + 0.96 * p.y, -0.96 * p.x + 0.28 * p.y);
    return 0.55 * vn(q * 0.24) + 0.3 * vn(r * 0.24 + 11.0) + 0.15 * vn(q * 0.62 + 17.0);
  }
};
DF d;
float2 p = UV * 8192.0;                                  // atlas pixels
float fw = max(length(ddx(p)), length(ddy(p)));          // atlas px per screen px
float fade = saturate(1.4 - fw * 0.9) * saturate(fw * 4.0);   // also off when magnified (no visible lattice)                   // grain only where it is resolved
float e = 0.8; float g0 = d.grain(p);
float gx = d.grain(p + float2(e, 0.0)) - g0, gy = d.grain(p + float2(0.0, e)) - g0;
float2 nxy = -float2(gx, gy) / e * 0.12 * Strength * fade;
// smudges / fingerprints (2-20 cm blotches) and wear-polish: roughness delta
float sm = 0.6 * d.vn(p * 0.006 + 3.0) + 0.4 * d.vn(p * 0.022 + 9.0);
float fp = smoothstep(0.62, 0.8, d.vn(p * 0.05 + 41.0)) * smoothstep(0.55, 0.7, d.vn(p * 0.011 + 5.0));
float rd = (sm - 0.5) * 0.22 - fp * 0.18;
// tone mottling +-4 % at ~10 cm
float tone = 1.0 + (d.vn(p * 0.01 + 77.0) - 0.5) * 0.08 + (g0 - 0.5) * 0.04 * fade;
return float4(nxy, rd * Strength, tone);
"""
NORM = r"""return normalize(float3(N.xy + D.xy, max(N.z, 0.05)));"""

m = eal.load_asset(DST)
find = lambda n: unreal.find_object(None, m.get_path_name() + ":" + n)
E = lambda cls, x, y: mel.create_material_expression(m, cls, x, y)
det = find("PanelDetailNode")
if det is None:
    nrm_src = mel.get_material_property_input_node(m, unreal.MaterialProperty.MP_NORMAL)
    rough_src = mel.get_material_property_input_node(m, unreal.MaterialProperty.MP_ROUGHNESS)
    base_src = mel.get_material_property_input_node(m, unreal.MaterialProperty.MP_BASE_COLOR)
    mask = find("PanelMaskNode")
    uv = E(unreal.MaterialExpressionTextureCoordinate, -2200, 2600)
    det = E(unreal.MaterialExpressionCustom, -1500, 2600); det.rename("PanelDetailNode")
    stg = E(unreal.MaterialExpressionScalarParameter, -2200, 2700); stg.set_editor_property("parameter_name", "DetailStrength"); stg.set_editor_property("default_value", 1.0)
    ins = []
    for n in ("UV", "Strength"):
        ci = unreal.CustomInput(); ci.set_editor_property("input_name", n); ins.append(ci)
    det.set_editor_property("inputs", ins); det.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    mel.connect_material_expressions(uv, "", det, "UV"); mel.connect_material_expressions(stg, "", det, "Strength")
    # normal
    nb = E(unreal.MaterialExpressionCustom, -700, 2600); nb.rename("PanelNormNode")
    ins = []
    for n in ("N", "D"):
        ci = unreal.CustomInput(); ci.set_editor_property("input_name", n); ins.append(ci)
    nb.set_editor_property("inputs", ins); nb.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    mel.connect_material_expressions(nrm_src, "", nb, "N"); mel.connect_material_expressions(det, "", nb, "D")
    mel.connect_material_property(nb, "", unreal.MaterialProperty.MP_NORMAL)
    # roughness: + detail delta, displays get glossy glass too
    dz = E(unreal.MaterialExpressionComponentMask, -1200, 2750)
    for c, v in zip("rgba", (False, False, True, False)): dz.set_editor_property(c, v)
    mel.connect_material_expressions(det, "", dz, "")
    ad = E(unreal.MaterialExpressionAdd, -900, 2750); mel.connect_material_expressions(rough_src, "", ad, "A"); mel.connect_material_expressions(dz, "", ad, "B")
    my = E(unreal.MaterialExpressionComponentMask, -1200, 2850)
    for c, v in zip("rgba", (False, True, False, False)): my.set_editor_property(c, v)
    mel.connect_material_expressions(mask, "", my, "")
    lg = E(unreal.MaterialExpressionLinearInterpolate, -700, 2800); lg.set_editor_property("const_b", 0.12)
    mel.connect_material_expressions(ad, "", lg, "A"); mel.connect_material_expressions(my, "", lg, "Alpha")
    sat = E(unreal.MaterialExpressionSaturate, -550, 2800); mel.connect_material_expressions(lg, "", sat, "")
    mel.connect_material_property(sat, "", unreal.MaterialProperty.MP_ROUGHNESS)
    # base colour tone
    dw = E(unreal.MaterialExpressionComponentMask, -1200, 2950)
    for c, v in zip("rgba", (False, False, False, True)): dw.set_editor_property(c, v)
    mel.connect_material_expressions(det, "", dw, "")
    bm = E(unreal.MaterialExpressionMultiply, -700, 2950); mel.connect_material_expressions(base_src, "", bm, "A"); mel.connect_material_expressions(dw, "", bm, "B")
    mel.connect_material_property(bm, "", unreal.MaterialProperty.MP_BASE_COLOR)
    log("graph built")
det.set_editor_property("code", DETAIL); det.set_editor_property("description", "PanelDetail")
find("PanelNormNode").set_editor_property("code", NORM)
mel.recompile_material(m); eal.save_loaded_asset(m)
mi = eal.load_asset(MAT + "/MI_Salon_VRay1")
if mi.get_editor_property("parent") != m:
    mi.set_editor_property("parent", m); mel.update_material_instance(mi); eal.save_loaded_asset(mi); log("MI_Salon_VRay1 -> M_MayaPBR_Live")
log("done")
