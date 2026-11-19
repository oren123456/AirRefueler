"""Make a small mesh containing only the Su-30 windscreen triangles (cut from Body1 by UV island) and use it
for the glass overlay instead of a full copy of Body1. A full-size translucent copy caused a screen-door
artifact over the clouds. Re-runnable."""
import unreal
GS = unreal
DST = "/Game/AirRefueler/Scene/SM_Su30_WindscreenGlass"
BOXES = [(0.783, 0.849, 0.295, 0.360), (0.029, 0.091, 0.441, 0.502), (0.191, 0.232, 0.531, 0.591)]
log = lambda *a: unreal.log("[WSMesh] " + " ".join(str(x) for x in a))
eal = unreal.EditorAssetLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

body = next(a for a in eas.get_all_level_actors() if a.get_actor_label() == "Body1")
src = body.get_component_by_class(unreal.StaticMeshComponent).static_mesh

dm = unreal.DynamicMesh()
dm, _ = GS.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(
    src, dm, unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
inb = lambda uv: any(a - 1e-3 <= uv.x % 1 <= b + 1e-3 and c - 1e-3 <= uv.y % 1 <= e + 1e-3 for a, b, c, e in BOXES)
n_ids = GS.GeometryScript_MeshQueries.get_num_triangle_i_ds(dm)
drop, keep = [], 0
for t in range(n_ids):
    if not GS.GeometryScript_MeshQueries.is_valid_triangle_id(dm, t):
        continue
    r = GS.GeometryScript_MeshQueries.get_triangle_u_vs(dm, 0, t)
    uv1, uv2, uv3, valid = r[0], r[1], r[2], r[3]
    if valid and inb(uv1) and inb(uv2) and inb(uv3):
        keep += 1
    else:
        drop.append(t)
log("triangles kept", keep, "of", n_ids)
lst = GS.GeometryScript_List.convert_array_to_index_list(drop, unreal.GeometryScriptIndexType.TRIANGLE)
GS.GeometryScript_MeshEdits.delete_triangles_from_mesh(dm, lst, False)

if eal.does_asset_exist(DST):
    eal.delete_asset(DST)
opts = unreal.GeometryScriptCreateNewStaticMeshAssetOptions()
opts.set_editor_property("enable_nanite", False)
opts.set_editor_property("enable_collision", False)
new_sm, _ = GS.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dm, DST, opts)
mi = eal.load_asset("/Game/AirRefueler/Materials/MI_Glass_Su30_Windscreen")
for i in range(len(new_sm.static_materials)):
    new_sm.set_material(i, mi)
eal.save_loaded_asset(new_sm)

glass = next(a for a in eas.get_all_level_actors() if a.get_actor_label() == "Body1_WindscreenGlass")
gc = glass.get_component_by_class(unreal.StaticMeshComponent)
gc.modify()
gc.set_static_mesh(new_sm)
for i in range(len(gc.get_materials())):
    gc.set_material(i, mi)
gc.set_editor_property("cast_shadow", False)

# Body1 no longer needs a full-resolution Nanite fallback
ns = src.get_editor_property("nanite_settings")
ns.set_editor_property("fallback_target", unreal.NaniteFallbackTarget.AUTO)
unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).set_nanite_settings(src, ns, True)
eal.save_loaded_asset(src)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
log("done:", new_sm.get_path_name(), "slots", len(new_sm.static_materials))
