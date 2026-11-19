"""Put the hose start (SimHose_RightPod) at the tail opening of the right pod (pCylinder1): ring centre measured from the mesh."""
import unreal
EXIT = unreal.Vector(1651.0, -546.0, 345.6)
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if a.get_actor_label() == "SimHose_RightPod":
        a.set_actor_location(EXIT, False, True)
        unreal.log("[HoseExit] moved to %s" % a.get_actor_location())
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
