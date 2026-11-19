"""Gather scene facts for the refuel simulator -> Saved/ClaudeShots/sim_probe.json"""
import unreal, json
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
acts = eas.get_all_level_actors()
def info(a):
    o, e = a.get_actor_bounds(False)
    p = a.get_attach_parent_actor()
    m = None
    c = a.get_component_by_class(unreal.StaticMeshComponent)
    if c: m = [str(c.mobility), c.static_mesh.get_name() if c.static_mesh else None, [x.get_name() for x in c.get_materials() if x]]
    return {"label": a.get_actor_label(), "class": a.get_class().get_name(), "loc": [round(v,1) for v in (a.get_actor_location().x, a.get_actor_location().y, a.get_actor_location().z)],
            "rot": [round(a.get_actor_rotation().pitch,1), round(a.get_actor_rotation().yaw,1), round(a.get_actor_rotation().roll,1)],
            "bmin": [round(o.x-e.x), round(o.y-e.y), round(o.z-e.z)], "bmax": [round(o.x+e.x), round(o.y+e.y), round(o.z+e.z)],
            "parent": p.get_actor_label() if p else None, "hidden": a.is_hidden_ed() if hasattr(a,'is_hidden_ed') else None, "mesh": m}
out = {"actors": []}
for a in acts:
    out["actors"].append(info(a))
pm = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem) if hasattr(unreal, "EditorAssetSubsystem") else None
out["cable_class"] = bool(getattr(unreal, "CableComponent", None))
out["world"] = unreal.EditorLevelLibrary.get_editor_world().get_name()
json.dump(out, open(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()) + "ClaudeShots/sim_probe.json", "w"), indent=0)
unreal.log("[SimProbe] %d actors" % len(out["actors"]))
