"""Place the refuel hose at the LEFT pod (pod2 / pCylinder11 tail opening, measured) and move the player Mirage
behind it with the same relative offset it had to the old right-pod hose."""
import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
log = lambda *x: unreal.log("[PlaceLeft] " + " ".join(str(v) for v in x))
EXIT = unreal.Vector(-1669.75, -535.5, 272.0)
OLD_EXIT = unreal.Vector(1651.0, -546.0, 345.6)
OLD_MIRAGE = unreal.Vector(1682.6, -9933.1, -224.0)
acts = {a.get_actor_label(): a for a in eas.get_all_level_actors()}
if "SimHose_LeftPod" in acts:
    eas.destroy_actor(acts["SimHose_LeftPod"])
bp = unreal.EditorAssetLibrary.load_asset("/Game/AirRefueler/Sim/BP_RefuelHose")
h = eas.spawn_actor_from_object(bp, EXIT, unreal.Rotator())
h.set_actor_label("SimHose_LeftPod")
p = acts["SimPlayer_Mirage"]
p.set_actor_location(OLD_MIRAGE + (EXIT - OLD_EXIT), False, True)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
log("hose at", h.get_actor_location(), "| Mirage at", p.get_actor_location())
