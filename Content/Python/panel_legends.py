"""Backlit panel legends on M_MayaPBR_Live: emissive += legend mask * LegendGlow * LegendColor.
Mask = T_PanelLegend (front-panel white markings, Tools/panel_legend.py, atlas UV) outside the UFCP face, and
T_UFCP_Mask.B (decal legends) inside it. Re-runnable."""
import unreal, os
eal = unreal.EditorAssetLibrary; mel = unreal.MaterialEditingLibrary; at = unreal.AssetToolsHelpers.get_asset_tools()
TEX = "/Game/AirRefueler/Models/Aircraft/Mirage/Textures"; DST = "/Game/AirRefueler/Models/Aircraft/Mirage/Materials/M_MayaPBR_Live"
root = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
log = lambda s: unreal.log("[Legends] " + s)
t = unreal.AssetImportTask(); t.filename = os.path.join(root, "Data", "Generated", "T_PanelLegend.png")
t.destination_path = TEX; t.destination_name = "T_PanelLegend"; t.automated = True; t.replace_existing = True; t.save = True
at.import_asset_tasks([t])
lt = eal.load_asset(TEX + "/T_PanelLegend")
lt.set_editor_property("srgb", False); lt.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_GRAYSCALE)
eal.save_loaded_asset(lt)
m = eal.load_asset(DST)
find = lambda n: unreal.find_object(None, m.get_path_name() + ":" + n)
E = lambda cls, x, y: mel.create_material_expression(m, cls, x, y)
CODE = "return lerp(A, D, In);"
ln = find("LegendNode")
if ln is None:
    emi_src = mel.get_material_property_input_node(m, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    log("emissive source " + emi_src.get_name())
    X, Y = -400, 4300
    uv = E(unreal.MaterialExpressionTextureCoordinate, X - 1200, Y)
    ls = E(unreal.MaterialExpressionTextureSample, X - 1000, Y); ls.rename("LegendSample")
    ls.set_editor_property("texture", lt); ls.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
    mel.connect_material_expressions(uv, "", ls, "UVs")
    inside = E(unreal.MaterialExpressionComponentMask, X - 1000, Y + 250)
    for c, v in zip("rgba", (False, False, True, False)): inside.set_editor_property(c, v)
    mel.connect_material_expressions(find("UfcpUVNode"), "", inside, "")
    ln = E(unreal.MaterialExpressionCustom, X - 700, Y); ln.rename("LegendNode")
    ins = []
    for n in ("A", "D", "In"):
        ci = unreal.CustomInput(); ci.set_editor_property("input_name", n); ins.append(ci)
    ln.set_editor_property("inputs", ins); ln.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    mel.connect_material_expressions(ls, "R", ln, "A"); mel.connect_material_expressions(find("UfcpMask"), "B", ln, "D"); mel.connect_material_expressions(inside, "", ln, "In")
    gp = E(unreal.MaterialExpressionScalarParameter, X - 700, Y + 200); gp.set_editor_property("parameter_name", "LegendGlow"); gp.set_editor_property("default_value", 200.0)
    cp = E(unreal.MaterialExpressionVectorParameter, X - 700, Y + 300); cp.set_editor_property("parameter_name", "LegendColor"); cp.set_editor_property("default_value", unreal.LinearColor(1.0, 0.88, 0.68, 1.0))
    m1 = E(unreal.MaterialExpressionMultiply, X - 450, Y + 100); mel.connect_material_expressions(ln, "", m1, "A"); mel.connect_material_expressions(gp, "", m1, "B")
    m2 = E(unreal.MaterialExpressionMultiply, X - 300, Y + 150); mel.connect_material_expressions(m1, "", m2, "A"); mel.connect_material_expressions(cp, "RGB", m2, "B")
    ad = E(unreal.MaterialExpressionAdd, X - 150, Y + 150); mel.connect_material_expressions(emi_src, "", ad, "A"); mel.connect_material_expressions(m2, "", ad, "B")
    mel.connect_material_property(ad, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    log("graph built")
ln.set_editor_property("code", CODE)
mel.recompile_material(m); eal.save_loaded_asset(m)
import sys
glow = float(sys.argv[1]) if len(sys.argv) > 1 else 40.0
for mi_name in ("MI_Salon_VRay1", "MI_Salon_VRay1_Cutout"):
    mi = eal.load_asset("/Game/AirRefueler/Models/Aircraft/Mirage/Materials/" + mi_name)
    mel.set_material_instance_scalar_parameter_value(mi, "LegendGlow", glow); mel.update_material_instance(mi); eal.save_loaded_asset(mi)
log("LegendGlow %.0f" % glow)
log("done")
