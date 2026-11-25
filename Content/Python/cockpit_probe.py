"""Writes PilotCam world transform + cockpit-panel related components/materials to Saved/ClaudeShots/cockpit_probe.txt"""
import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
out = []
for a in eas.get_all_level_actors():
    if a.get_class().get_name().startswith("BP_MiragePawn"):
        for c in a.get_components_by_class(unreal.SceneComponent):
            if "Cam" in c.get_name():
                out.append("%s loc=%s rot=%s" % (c.get_name(), c.get_world_location(), c.get_world_rotation()))
        out.append("pawn rot %s" % a.get_actor_rotation())
names = ["Cockpit_Panel", "Cockpit_Panel2", "Devices", "Devices2", "Devices3", "Control_Device", "Control_Device2", "Cockpit", "Mirage_HUDGlass", "Cockpit_Grid"]
for a in eas.get_all_level_actors():
    if a.get_actor_label() in names:
        smc = a.static_mesh_component; m = smc.static_mesh
        o, e = a.get_actor_bounds(False)
        mats = [smc.get_material(i).get_path_name() if smc.get_material(i) else None for i in range(smc.get_num_materials())]
        out.append("%s mesh=%s parent=%s bounds c=(%.0f,%.0f,%.0f) e=(%.0f,%.0f,%.0f) tris=%s mats=%s" % (a.get_actor_label(), m.get_path_name() if m else None,
            a.get_attach_parent_actor().get_actor_label() if a.get_attach_parent_actor() else None, o.x, o.y, o.z, e.x, e.y, e.z,
            m.get_num_triangles(0) if m else 0, mats))
open(unreal.Paths.project_saved_dir() + "ClaudeShots/cockpit_probe.txt", "w").write("\n".join(out))
