"""Place the imported boom assembly (Datasmith scene actor BOOM_ASSY_767-300_3D_CAMERAS; CAD: hinge at origin, boom along
-X) under the 767's aft fuselage: yaw 90 (boom trails aft = -Y), pitch +ELEV (tip down), attached to bo_767. argv: x y z elev"""
import unreal, sys, json
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
x, y, z, el = [float(v) for v in sys.argv[1:5]] if len(sys.argv) > 4 else (0.0, -1550.0, 200.0, 30.0)
acts = {a.get_actor_label(): a for a in eas.get_all_level_actors()}
b = next(a for a in eas.get_all_level_actors() if a.get_class().get_name().startswith("DatasmithSceneActor") and a.get_actor_label().startswith("BOOM_ASSY"))
b.detach_from_actor(unreal.DetachmentRule.KEEP_WORLD, unreal.DetachmentRule.KEEP_WORLD, unreal.DetachmentRule.KEEP_WORLD)
b.set_actor_location_and_rotation(unreal.Vector(x, y, z), unreal.Rotator(roll=0.0, pitch=el, yaw=90.0), False, True)
b.attach_to_actor(acts["bo_767"], "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
lo = [1e18]*3; hi = [-1e18]*3
for a in eas.get_all_level_actors():
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        m = c.static_mesh
        if m and m.get_path_name().startswith("/Game/AirRefueler/Boom"):
            o, e, _ = unreal.SystemLibrary.get_component_bounds(c)
            for k, (oo, ee) in enumerate(((o.x, e.x), (o.y, e.y), (o.z, e.z))):
                lo[k] = min(lo[k], oo - ee); hi[k] = max(hi[k], oo + ee)
open(r"D:/GitHub/AirRefueler/Saved/ClaudeShots/boom_place.json", "w").write(json.dumps({"lo": [round(v) for v in lo], "hi": [round(v) for v in hi]}))
