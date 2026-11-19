"""Turn part of an opaque mesh into glass, selected by UV islands.
argv: actor_label  src_MI  mask_png_stem(Data/Generated)  glass_MI  overlay_label  r g b opacity  u0 u1 v0 v1 [u0 u1 v0 v1 ...]
- actor gets a cut-out copy of src_MI (Masked, hole where the mask is white)
- a small mesh with only those UV islands is extracted (Geometry Script) and placed as overlay_label,
  attached to the actor, with a translucent glass MI (M_MayaGlassOverlay). Re-runnable."""
import os, sys, unreal
a = sys.argv[1:]
LABEL, SRC_MI, MASK, GLASS_MI, OVL = a[0], a[1], a[2], a[3], a[4]
COLOR = unreal.LinearColor(float(a[5]), float(a[6]), float(a[7]), 1.0)
OPACITY = float(a[8])
nums = [float(x) for x in a[9:]]
BOXES = [tuple(nums[i:i + 4]) for i in range(0, len(nums), 4)]
MAT, TEX, SCN = "/Game/AirRefueler/Materials", "/Game/AirRefueler/Textures", "/Game/AirRefueler/Scene"
GEN = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()), "Data", "Generated")
at = unreal.AssetToolsHelpers.get_asset_tools(); eal = unreal.EditorAssetLibrary; mel = unreal.MaterialEditingLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
log = lambda *x: unreal.log("[GlassPart] " + " ".join(str(v) for v in x))

# mask texture
tname = "T_" + MASK.replace("-", "_")
t = unreal.AssetImportTask(); t.filename = os.path.join(GEN, MASK + ".png"); t.destination_path = TEX
t.destination_name = tname; t.automated = True; t.replace_existing = True
at.import_asset_tasks([t])
mask = eal.load_asset(TEX + "/" + tname); mask.set_editor_property("srgb", True); mask.set_editor_property("max_texture_size", 2048)
eal.save_loaded_asset(mask)

# cut-out hull material
cut_path = MAT + "/" + SRC_MI + "_Cutout"
if not eal.does_asset_exist(cut_path):
    eal.duplicate_asset(MAT + "/" + SRC_MI, cut_path)
cut = eal.load_asset(cut_path)
mel.set_material_instance_texture_parameter_value(cut, "CutoutMask", mask)
mel.set_material_instance_scalar_parameter_value(cut, "UseCutout", 1.0)
bo = cut.get_editor_property("base_property_overrides")
bo.set_editor_property("override_blend_mode", True); bo.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
cut.set_editor_property("base_property_overrides", bo)
mel.update_material_instance(cut); eal.save_loaded_asset(cut)

# glass material
ov = eal.load_asset(MAT + "/M_MayaGlassOverlay")
gp = MAT + "/" + GLASS_MI
gi = eal.load_asset(gp) if eal.does_asset_exist(gp) else at.create_asset(GLASS_MI, MAT, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
mel.set_material_instance_parent(gi, ov)
white = unreal.load_asset("/Engine/EngineResources/WhiteSquareTexture")
mel.set_material_instance_texture_parameter_value(gi, "GlassMask", white)     # whole extracted mesh is glass
mel.set_material_instance_vector_parameter_value(gi, "GlassColor", COLOR)
mel.set_material_instance_scalar_parameter_value(gi, "GlassOpacity", OPACITY)
mel.update_material_instance(gi); eal.save_loaded_asset(gi)

# apply cut-out to the actor
act = next(x for x in eas.get_all_level_actors() if x.get_actor_label() == LABEL)
comp = act.get_component_by_class(unreal.StaticMeshComponent)
comp.modify()
for i in range(len(comp.get_materials())):
    comp.set_material(i, cut)

# extract the glass triangles into their own mesh
G = unreal
dm = unreal.DynamicMesh()
dm, _ = G.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(comp.static_mesh, dm, unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
inb = lambda uv: any(u0 - 1e-3 <= uv.x % 1 <= u1 + 1e-3 and v0 - 1e-3 <= uv.y % 1 <= v1 + 1e-3 for u0, u1, v0, v1 in BOXES)
drop, keep = [], 0
for tid in range(G.GeometryScript_MeshQueries.get_num_triangle_i_ds(dm)):
    if not G.GeometryScript_MeshQueries.is_valid_triangle_id(dm, tid):
        continue
    r = G.GeometryScript_MeshQueries.get_triangle_u_vs(dm, 0, tid)
    if r[3] and inb(r[0]) and inb(r[1]) and inb(r[2]):
        keep += 1
    else:
        drop.append(tid)
G.GeometryScript_MeshEdits.delete_triangles_from_mesh(dm, G.GeometryScript_List.convert_array_to_index_list(drop, unreal.GeometryScriptIndexType.TRIANGLE), False)
dst = SCN + "/SM_" + OVL
if eal.does_asset_exist(dst):
    eal.delete_asset(dst)
opts = unreal.GeometryScriptCreateNewStaticMeshAssetOptions()
opts.set_editor_property("enable_nanite", False); opts.set_editor_property("enable_collision", False)
sm, _ = G.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dm, dst, opts)
for i in range(len(sm.static_materials)):
    sm.set_material(i, gi)
eal.save_loaded_asset(sm)

for x in eas.get_all_level_actors():
    if x.get_actor_label() == OVL:
        eas.destroy_actor(x)
g = eas.spawn_actor_from_object(sm, act.get_actor_location(), act.get_actor_rotation())
g.set_actor_label(OVL)
gc = g.get_component_by_class(unreal.StaticMeshComponent)
gc.set_mobility(unreal.ComponentMobility.MOVABLE); gc.set_editor_property("cast_shadow", False)
for i in range(len(gc.get_materials())):
    gc.set_material(i, gi)
g.attach_to_actor(act, "", unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.SNAP_TO_TARGET, False)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
log(LABEL, "-> glass triangles", keep, "| cut-out", cut.get_name(), "| overlay", OVL)
