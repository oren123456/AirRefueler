"""Import the 767 refuelling boom STEP (CATIA AP242) with Datasmith CAD into /Game/AirRefueler/Boom (actors into the
current level under a Datasmith scene actor). Logs counts / bounds to Saved/ClaudeShots/boom_import.json."""
import unreal, json, time
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
p = r"D:/GitHub/AirRefueler/Data/BOOM_ASSY_767-300_3D_CAMERAS.stp"
r = {"has_datasmith": hasattr(unreal, "DatasmithSceneElement")}
t0 = time.time()
scene = unreal.DatasmithSceneElement.construct_datasmith_scene_from_file(p)
r["scene"] = scene is not None
if scene:
    to = scene.get_options(unreal.DatasmithCommonTessellationOptions)
    if to:
        to.options.chord_tolerance = 0.1; to.options.max_edge_length = 0.0; to.options.normal_tolerance = 15.0
        r["tess"] = "set"
    res = scene.import_scene("/Game/AirRefueler/Boom")
    r["secs"] = round(time.time() - t0, 1)
    try:
        acts = list(res.imported_actors); meshes = list(res.imported_meshes)
        r["actors"] = len(acts); r["meshes"] = len(meshes)
        r["scene_actor"] = res.imported_scene_actor.get_actor_label() if res.imported_scene_actor else None
        if res.imported_scene_actor:
            o, e = res.imported_scene_actor.get_actor_bounds(False)
            r["bounds"] = [round(o.x), round(o.y), round(o.z), round(e.x), round(e.y), round(e.z)]
        r["names"] = [a.get_actor_label() for a in acts[:25]]
    except Exception as ex:
        r["res_err"] = str(ex)[:300]
    scene.destroy_scene()
open(r"D:/GitHub/AirRefueler/Saved/ClaudeShots/boom_import.json", "w").write(json.dumps(r, indent=1))
