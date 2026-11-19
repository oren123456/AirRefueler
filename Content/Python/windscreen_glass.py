"""Su-30 front windscreen glass. The windscreen is part of the big Body1 hull mesh (black in the texture,
not in the VRay refraction mask), so the whole mesh can't go translucent. Instead:
  1. Body1 gets a cut-out copy of its hull material (Masked, holes where Su-30_Body1_Windscreen_Mask is white).
  2. A second copy of the Body1 mesh, attached to Body1, draws only the windscreen as translucent glass.
Also reverts MI_Glass_Su30 to the original refraction mask. Re-runnable."""
import os, unreal

MAT = "/Game/AirRefueler/Materials"
TEX = "/Game/AirRefueler/Textures"
DATA = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()), "Data", "Generated")
at = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
log = lambda *a: unreal.log("[Windscreen] " + " ".join(str(x) for x in a))

def import_tex(stem):
    name = "T_" + stem.replace("-", "_")
    path = TEX + "/" + name
    t = unreal.AssetImportTask()
    t.filename = os.path.join(DATA, stem + ".png")
    t.destination_path = TEX
    t.destination_name = name
    t.automated = True
    t.replace_existing = True
    at.import_asset_tasks([t])
    tex = eal.load_asset(path)
    tex.set_editor_property("srgb", True)
    tex.set_editor_property("max_texture_size", 2048)
    eal.save_loaded_asset(tex)
    return tex

# ---- 0. revert the canopy glass mask (the earlier "fix" painted the canopy's rear fairing)
orig = eal.load_asset(TEX + "/T_Su_30_Body_Refraction")
mi_can = eal.load_asset(MAT + "/MI_Glass_Su30")
mel.set_material_instance_texture_parameter_value(mi_can, "RefractionTex", orig)
mel.update_material_instance(mi_can)
eal.save_loaded_asset(mi_can)
if eal.does_asset_exist(TEX + "/T_Su_30_Body_Refraction_Fixed"):
    eal.delete_asset(TEX + "/T_Su_30_Body_Refraction_Fixed")

mask = import_tex("Su-30_Body1_Windscreen_Mask")
white = unreal.load_asset("/Engine/EngineResources/WhiteSquareTexture")

# ---- 1. cut-out support in M_MayaPBR (only active when an MI switches the blend mode to Masked)
master = eal.load_asset(MAT + "/M_MayaPBR")
if not mel.get_material_property_input_node(master, unreal.MaterialProperty.MP_OPACITY_MASK):
    E = lambda cls, x, y: mel.create_material_expression(master, cls, x, y)
    cm = E(unreal.MaterialExpressionTextureSampleParameter2D, -800, 900)
    cm.set_editor_property("parameter_name", "CutoutMask")
    cm.set_editor_property("texture", white)
    use = E(unreal.MaterialExpressionScalarParameter, -800, 1150)
    use.set_editor_property("parameter_name", "UseCutout")
    use.set_editor_property("default_value", 0.0)
    mul = E(unreal.MaterialExpressionMultiply, -500, 950)
    mel.connect_material_expressions(cm, "R", mul, "A")
    mel.connect_material_expressions(use, "", mul, "B")
    inv = E(unreal.MaterialExpressionOneMinus, -300, 950)
    mel.connect_material_expressions(mul, "", inv, "")
    mel.connect_material_property(inv, "", unreal.MaterialProperty.MP_OPACITY_MASK)
    mel.recompile_material(master)
    eal.save_loaded_asset(master)
    log("M_MayaPBR: CutoutMask/UseCutout added")

cut_path = MAT + "/MI_Su_30_Body_VRay_Cutout"
if not eal.does_asset_exist(cut_path):
    eal.duplicate_asset(MAT + "/MI_Su_30_Body_VRay", cut_path)
cut = eal.load_asset(cut_path)
mel.set_material_instance_texture_parameter_value(cut, "CutoutMask", mask)
mel.set_material_instance_scalar_parameter_value(cut, "UseCutout", 1.0)
bo = cut.get_editor_property("base_property_overrides")
bo.set_editor_property("override_blend_mode", True)
bo.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
cut.set_editor_property("base_property_overrides", bo)
mel.update_material_instance(cut)
eal.save_loaded_asset(cut)

# ---- 2. glass-only overlay material
ov_path = MAT + "/M_MayaGlassOverlay"
if not eal.does_asset_exist(ov_path):
    m = at.create_asset("M_MayaGlassOverlay", MAT, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property("translucency_lighting_mode", unreal.TranslucencyLightingMode.TLM_SURFACE)
    E = lambda cls, x, y: mel.create_material_expression(m, cls, x, y)
    mk = E(unreal.MaterialExpressionTextureSampleParameter2D, -800, 0)
    mk.set_editor_property("parameter_name", "GlassMask")
    mk.set_editor_property("texture", white)
    col = E(unreal.MaterialExpressionVectorParameter, -800, -250)
    col.set_editor_property("parameter_name", "GlassColor")
    col.set_editor_property("default_value", unreal.LinearColor(0.02, 0.025, 0.03, 1))
    mel.connect_material_property(col, "", unreal.MaterialProperty.MP_BASE_COLOR)
    op = E(unreal.MaterialExpressionScalarParameter, -800, 250)
    op.set_editor_property("parameter_name", "GlassOpacity")
    op.set_editor_property("default_value", 0.15)
    om = E(unreal.MaterialExpressionMultiply, -450, 150)
    mel.connect_material_expressions(mk, "R", om, "A")
    mel.connect_material_expressions(op, "", om, "B")
    mel.connect_material_property(om, "", unreal.MaterialProperty.MP_OPACITY)
    sp = E(unreal.MaterialExpressionMultiply, -450, 350)          # no reflections outside the glass
    mel.connect_material_expressions(mk, "R", sp, "A")
    half = E(unreal.MaterialExpressionConstant, -650, 450)
    half.set_editor_property("r", 0.5)
    mel.connect_material_expressions(half, "", sp, "B")
    mel.connect_material_property(sp, "", unreal.MaterialProperty.MP_SPECULAR)
    rg = E(unreal.MaterialExpressionScalarParameter, -450, 550)
    rg.set_editor_property("parameter_name", "GlassRoughness")
    rg.set_editor_property("default_value", 0.03)
    mel.connect_material_property(rg, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.recompile_material(m)
    eal.save_loaded_asset(m)
ov = eal.load_asset(ov_path)
gi_path = MAT + "/MI_Glass_Su30_Windscreen"
gi = eal.load_asset(gi_path) if eal.does_asset_exist(gi_path) else at.create_asset(
    "MI_Glass_Su30_Windscreen", MAT, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
mel.set_material_instance_parent(gi, ov)
mel.set_material_instance_texture_parameter_value(gi, "GlassMask", mask)
mel.set_material_instance_vector_parameter_value(gi, "GlassColor", unreal.LinearColor(0.02, 0.025, 0.03, 1))
mel.set_material_instance_scalar_parameter_value(gi, "GlassOpacity", 0.15)
mel.update_material_instance(gi)
eal.save_loaded_asset(gi)

# ---- 3. apply to Body1 + overlay actor
body = next(a for a in eas.get_all_level_actors() if a.get_actor_label() == "Body1")
bc = body.get_component_by_class(unreal.StaticMeshComponent)
# Body1 is Nanite; the translucent overlay can't use Nanite and falls back to the fallback mesh.
# Default fallback is decimated -> make it full resolution so the glass matches the hull exactly.
ns = bc.static_mesh.get_editor_property("nanite_settings")
ns.set_editor_property("fallback_target", unreal.NaniteFallbackTarget.PERCENT_TRIANGLES)
ns.set_editor_property("fallback_percent_triangles", 1.0)
unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).set_nanite_settings(bc.static_mesh, ns, True)
eal.save_loaded_asset(bc.static_mesh)
bc.modify()
for i in range(len(bc.get_materials())):
    bc.set_material(i, cut)
for a in eas.get_all_level_actors():
    if a.get_actor_label() == "Body1_WindscreenGlass":
        eas.destroy_actor(a)
glass = eas.spawn_actor_from_object(bc.static_mesh, body.get_actor_location(), body.get_actor_rotation())
glass.set_actor_label("Body1_WindscreenGlass")
gc = glass.get_component_by_class(unreal.StaticMeshComponent)
gc.set_mobility(unreal.ComponentMobility.MOVABLE)
for i in range(len(gc.get_materials())):
    gc.set_material(i, gi)
gc.set_editor_property("cast_shadow", False)
glass.attach_to_actor(body, "", unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.SNAP_TO_TARGET,
                      unreal.AttachmentRule.SNAP_TO_TARGET, False)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
log("done: Body1 ->", cut.get_name(), "| overlay ->", gi.get_name())
