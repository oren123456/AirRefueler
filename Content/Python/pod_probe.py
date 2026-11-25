"""Pod / drogue geometry near the hose actor -> Saved/ClaudeShots/pod_probe.txt"""
import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
gw = unreal.EditorLevelLibrary.get_game_world()   # read-only from PIE if it is running
ALL = (lambda: unreal.GameplayStatics.get_all_actors_of_class(gw, unreal.Actor)) if gw else eas.get_all_level_actors
out = ["world: %s" % ("PIE" if gw else "editor")]
h = [a for a in ALL() if a.get_class().get_name().startswith("BP_RefuelHose")][0]
hl = h.get_actor_location(); out.append("hose actor %s rot %s state=%s hoselen=%s" % (hl, h.get_actor_rotation(), h.get_editor_property("State"), h.get_editor_property("HoseLen")))
for c in h.get_components_by_class(unreal.SceneComponent):
    line = "comp %s %s rel=%s world=%s" % (c.get_name(), c.get_class().get_name(), c.get_editor_property("relative_location"), c.get_world_location())
    if isinstance(c, unreal.StaticMeshComponent) and c.static_mesh:
        bb = c.static_mesh.get_bounding_box(); line += " meshbb min=%s max=%s scale=%s" % (bb.min, bb.max, c.get_editor_property("relative_scale3d"))
    out.append(line)
for a in ALL():
    if isinstance(a, unreal.StaticMeshActor):
        o, e = a.get_actor_bounds(False)
        if abs(o.x - hl.x) < e.x + 50 and abs(o.y - hl.y) < e.y + 50 and abs(o.z - hl.z) < e.z + 50 and e.length() < 3000:
            out.append("near %s c=(%.0f,%.0f,%.0f) e=(%.0f,%.0f,%.0f) mesh=%s" % (a.get_actor_label(), o.x, o.y, o.z, e.x, e.y, e.z, a.static_mesh_component.static_mesh.get_name() if a.static_mesh_component.static_mesh else None))
open(unreal.Paths.project_saved_dir() + "ClaudeShots/pod_probe.txt", "w").write("\n".join(out))
