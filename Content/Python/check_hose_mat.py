import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
h = next(a for a in eas.get_all_level_actors() if a.get_actor_label() == "SimHose_LeftPod")
c = h.get_component_by_class(unreal.CableComponent)
unreal.log("[HoseMat] instance mat=%s overrides=%s tile=%s segs=%s grav=%s" % (c.get_material(0), c.get_editor_property("override_materials"), c.get_editor_property("tile_material"), c.get_editor_property("num_segments"), c.get_editor_property("cable_gravity_scale")))
