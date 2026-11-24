"""Separate the Mirage refuelling probe (nozzle 640 tris + arm 180 tris, the two islands nearest ProbeTip) from
Mesh_ncl_365 ("Detals") into SM_Mirage_RefuelProbe (same local space -> drops in exactly in place).
Removes those triangles from Mesh_ncl_365, adds level actor "RefuelProbe" attached like Detals.
Uses Saved/ClaudeShots/probe_islands.json from inspect_probe_mesh.py. argv[1]=='go' to apply."""
import unreal, json, sys
G = unreal
GO = len(sys.argv) > 1 and sys.argv[1] == "go"
log = lambda s: unreal.log("[SplitProbe] " + s)
eal = unreal.EditorAssetLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
J = json.load(open(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()) + "ClaudeShots/probe_islands.json"))
isl = J["islands"][:2]
assert sorted(i["n"] for i in isl) == [180, 640], [i["n"] for i in isl]
probe = set(t for i in isl for t in i["tris"])
SRC = J["mesh"].split(".")[0]
DST = SRC.rsplit("/", 1)[0] + "/SM_Mirage_RefuelProbe"
src = eal.load_asset(SRC)
nan = src.get_editor_property("nanite_settings").enabled
log("src %s nanite=%s probe tris=%d" % (SRC, nan, len(probe)))
def load_dm():
    dm = unreal.DynamicMesh()
    dm, _ = G.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(src, dm, unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
    return dm
def keep_only(dm, keep):
    n = G.GeometryScript_MeshQueries.get_num_triangle_i_ds(dm)
    drop = [t for t in range(n) if G.GeometryScript_MeshQueries.is_valid_triangle_id(dm, t) and ((t in probe) != keep)]
    G.GeometryScript_MeshEdits.delete_triangles_from_mesh(dm, G.GeometryScript_List.convert_array_to_index_list(drop, unreal.GeometryScriptIndexType.TRIANGLE), False)
    return n - len(drop)
dp = load_dm(); np_ = keep_only(dp, True)
dr = load_dm(); nr = keep_only(dr, False)
log("probe mesh tris=%d, rest tris=%d (orig %d)" % (np_, nr, J["ntris"]))
if GO:
    # 1) new probe asset
    if eal.does_asset_exist(DST): eal.delete_asset(DST)
    opts = unreal.GeometryScriptCreateNewStaticMeshAssetOptions()
    opts.set_editor_property("enable_nanite", nan)
    opts.set_editor_property("enable_collision", False)
    sm, _ = G.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dp, DST, opts)
    for i in range(len(sm.static_materials)):
        sm.set_material(i, src.static_materials[0].material_interface)
    sm.get_editor_property("body_setup").set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    eal.save_loaded_asset(sm)
    # 2) remove probe from Mesh_ncl_365 (in place, keeps its settings/materials)
    wo = unreal.GeometryScriptCopyMeshToAssetOptions()
    wo.set_editor_property("replace_materials", False)
    G.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dr, src, wo, unreal.GeometryScriptMeshWriteLOD())
    eal.save_loaded_asset(src)
    # 3) level actor next to Detals
    det = next(a for a in eas.get_all_level_actors() if a.get_actor_label() == J["owner"])
    dc = det.get_component_by_class(unreal.StaticMeshComponent)
    na = eas.spawn_actor_from_class(unreal.StaticMeshActor, det.get_actor_location(), det.get_actor_rotation())
    na.set_actor_label("RefuelProbe")
    na.set_actor_scale3d(det.get_actor_scale3d())
    nc = na.static_mesh_component
    nc.set_mobility(dc.mobility)
    nc.set_static_mesh(sm)
    nc.set_world_transform(dc.get_world_transform(), False, True)
    nc.set_collision_profile_name(dc.get_collision_profile_name())
    p = det.get_attach_parent_actor()
    if p: na.attach_to_actor(p, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
    na.set_folder_path(det.get_folder_path())
    log("actor RefuelProbe parent=%s profile=%s" % (p.get_actor_label() if p else None, nc.get_collision_profile_name()))
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    log("done")
