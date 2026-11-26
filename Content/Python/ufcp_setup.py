"""UFCP (khaki HUD-control box face) decal on M_MayaPBR_Live. Imports Data/Generated/T_UFCP_{Color,Normal,Mask}.png
(Tools/ufcp_decal.py) and overrides base colour / normal / roughness / emissive inside the box face's atlas rect
(atlas px cols 2876..3024 = face bottom..top, rows 1134..1285 = pilot left..right). Re-runnable."""
import unreal, os
eal = unreal.EditorAssetLibrary; mel = unreal.MaterialEditingLibrary; at = unreal.AssetToolsHelpers.get_asset_tools()
TEX = "/Game/AirRefueler/Models/Aircraft/Mirage/Textures"; MAT = "/Game/AirRefueler/Models/Aircraft/Mirage/Materials"; DST = MAT + "/M_MayaPBR_Live"
root = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
log = lambda s: unreal.log("[UFCP] " + s)
tex = {}
for n in ("T_UFCP_Color", "T_UFCP_Normal", "T_UFCP_Mask"):
    t = unreal.AssetImportTask(); t.filename = os.path.join(root, "Data", "Generated", n + ".png")
    t.destination_path = TEX; t.destination_name = n; t.automated = True; t.replace_existing = True; t.save = True
    at.import_asset_tasks([t])
    a = eal.load_asset(TEX + "/" + n)
    a.set_editor_property("address_x", unreal.TextureAddress.TA_CLAMP); a.set_editor_property("address_y", unreal.TextureAddress.TA_CLAMP)
    if n == "T_UFCP_Normal":
        a.set_editor_property("srgb", False); a.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
    if n == "T_UFCP_Mask":
        a.set_editor_property("srgb", False); a.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
    eal.save_loaded_asset(a); tex[n] = a
UVCODE = r"""
float2 p = UV * 8192.0;
float2 d = float2((p.y - 1134.0) / 151.0, (3024.0 - p.x) / 148.0);
float in_ = (d.x >= 0.0 && d.x <= 1.0 && d.y >= 0.0 && d.y <= 1.0) ? 1.0 : 0.0;
return float3(saturate(d), in_);
"""
m = eal.load_asset(DST)
find = lambda n: unreal.find_object(None, m.get_path_name() + ":" + n)
E = lambda cls, x, y: mel.create_material_expression(m, cls, x, y)
uvn = find("UfcpUVNode")
if uvn is None:
    base_src = mel.get_material_property_input_node(m, unreal.MaterialProperty.MP_BASE_COLOR)
    nrm_src = mel.get_material_property_input_node(m, unreal.MaterialProperty.MP_NORMAL)
    rgh_src = mel.get_material_property_input_node(m, unreal.MaterialProperty.MP_ROUGHNESS)
    emi_src = mel.get_material_property_input_node(m, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    log("sources %s %s %s %s" % (base_src.get_name(), nrm_src.get_name(), rgh_src.get_name(), emi_src.get_name()))
    X = -400; Y = 3300
    uv = E(unreal.MaterialExpressionTextureCoordinate, X - 1400, Y)
    uvn = E(unreal.MaterialExpressionCustom, X - 1200, Y); uvn.rename("UfcpUVNode")
    ci = unreal.CustomInput(); ci.set_editor_property("input_name", "UV"); uvn.set_editor_property("inputs", [ci])
    uvn.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    mel.connect_material_expressions(uv, "", uvn, "UV")
    rg = E(unreal.MaterialExpressionComponentMask, X - 1000, Y)
    for c, v in zip("rgba", (True, True, False, False)): rg.set_editor_property(c, v)
    mel.connect_material_expressions(uvn, "", rg, "")
    bm = E(unreal.MaterialExpressionComponentMask, X - 1000, Y + 120)
    for c, v in zip("rgba", (False, False, True, False)): bm.set_editor_property(c, v)
    mel.connect_material_expressions(uvn, "", bm, "")
    def samp(name, st, y):
        s = E(unreal.MaterialExpressionTextureSample, X - 800, Y + y); s.rename(name)
        s.set_editor_property("texture", tex[{"UfcpColor": "T_UFCP_Color", "UfcpNormal": "T_UFCP_Normal", "UfcpMask": "T_UFCP_Mask"}[name]])
        s.set_editor_property("sampler_type", st)
        mel.connect_material_expressions(rg, "", s, "UVs"); return s
    sc = samp("UfcpColor", unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, 0)
    sn = samp("UfcpNormal", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL, 250)
    sm = samp("UfcpMask", unreal.MaterialSamplerType.SAMPLERTYPE_MASKS, 500)
    # base colour
    lb = E(unreal.MaterialExpressionLinearInterpolate, X - 400, Y)
    mel.connect_material_expressions(base_src, "", lb, "A"); mel.connect_material_expressions(sc, "RGB", lb, "B"); mel.connect_material_expressions(bm, "", lb, "Alpha")
    mel.connect_material_property(lb, "", unreal.MaterialProperty.MP_BASE_COLOR)
    # normal
    ln = E(unreal.MaterialExpressionLinearInterpolate, X - 400, Y + 250)
    mel.connect_material_expressions(nrm_src, "", ln, "A"); mel.connect_material_expressions(sn, "RGB", ln, "B"); mel.connect_material_expressions(bm, "", ln, "Alpha")
    mel.connect_material_property(ln, "", unreal.MaterialProperty.MP_NORMAL)
    # roughness (mask G)
    lr = E(unreal.MaterialExpressionLinearInterpolate, X - 400, Y + 500)
    mel.connect_material_expressions(rgh_src, "", lr, "A"); mel.connect_material_expressions(sm, "G", lr, "B"); mel.connect_material_expressions(bm, "", lr, "Alpha")
    mel.connect_material_property(lr, "", unreal.MaterialProperty.MP_ROUGHNESS)
    # emissive += colour * mask R * inside * UfcpGlow
    gp = E(unreal.MaterialExpressionScalarParameter, X - 800, Y + 750); gp.set_editor_property("parameter_name", "UfcpGlow"); gp.set_editor_property("default_value", 1500.0)
    m1 = E(unreal.MaterialExpressionMultiply, X - 600, Y + 650); mel.connect_material_expressions(sm, "R", m1, "A"); mel.connect_material_expressions(bm, "", m1, "B")
    m2 = E(unreal.MaterialExpressionMultiply, X - 500, Y + 700); mel.connect_material_expressions(m1, "", m2, "A"); mel.connect_material_expressions(gp, "", m2, "B")
    m3 = E(unreal.MaterialExpressionMultiply, X - 400, Y + 700); mel.connect_material_expressions(sc, "RGB", m3, "A"); mel.connect_material_expressions(m2, "", m3, "B")
    ae = E(unreal.MaterialExpressionAdd, X - 250, Y + 700); mel.connect_material_expressions(emi_src, "", ae, "A"); mel.connect_material_expressions(m3, "", ae, "B")
    mel.connect_material_property(ae, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    log("graph built")
else:
    for n, k in (("UfcpColor", "T_UFCP_Color"), ("UfcpNormal", "T_UFCP_Normal"), ("UfcpMask", "T_UFCP_Mask")):
        find(n).set_editor_property("texture", tex[k])
uvn.set_editor_property("code", UVCODE); uvn.set_editor_property("description", "UFCP decal UV")
mel.recompile_material(m); eal.save_loaded_asset(m)
log("done")
