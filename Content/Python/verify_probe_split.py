import unreal, json, time
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
log = lambda s: unreal.log("[VerifyProbe] " + s)
acts = {a.get_actor_label(): a for a in eas.get_all_level_actors()}
rp, det = acts["RefuelProbe"], acts["Detals"]
o, e = rp.get_actor_bounds(False)
log("RefuelProbe bounds min=(%.1f,%.1f,%.1f) max=(%.1f,%.1f,%.1f)" % (o.x-e.x, o.y-e.y, o.z-e.z, o.x+e.x, o.y+e.y, o.z+e.z))
for a in (rp, det):
    sm = a.static_mesh_component.static_mesh
    log("%s mesh=%s tris=%d" % (a.get_actor_label(), sm.get_name(), sm.get_num_triangles(0)))
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
ues.set_level_viewport_camera_info(o + unreal.Vector(-160, 60, 50), unreal.Rotator(roll=0.0, pitch=-15.0, yaw=-20.0))
st = {"t": time.time(), "h": None}
def tick(dt):
    if time.time() - st["t"] > 1.5:
        unreal.SystemLibrary.execute_console_command(None, "HighResShot 1"); unreal.unregister_slate_post_tick_callback(st["h"]); log("shot")
st["h"] = unreal.register_slate_post_tick_callback(tick)
for p in ("/Game/AirRefueler/Models/Aircraft/Mirage/Mesh_ncl_365", "/Game/AirRefueler/Models/Aircraft/Mirage/SM_Mirage_RefuelProbe"):
    sm = unreal.load_asset(p); dm = unreal.DynamicMesh()
    dm, _ = unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(sm, dm, unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
    log("%s source tris=%d nanite=%s ctf=%s" % (p.rsplit("/",1)[1], unreal.GeometryScript_MeshQueries.get_num_triangle_i_ds(dm), sm.get_editor_property("nanite_settings").enabled, sm.get_editor_property("body_setup").get_editor_property("collision_trace_flag")))
