import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
h = next(a for a in eas.get_all_level_actors() if a.get_actor_label() == "SimHose_LeftPod")
for c in h.get_components_by_class(unreal.SceneComponent):
    p = c.get_attach_parent()
    unreal.log("[ChkLights] %s parent=%s world-actor=%s visible=%s" % (c.get_name(), p.get_name() if p else None, c.get_world_location() - h.get_actor_location(), c.is_visible()))
