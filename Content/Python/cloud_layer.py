"""Cloud deck closer to the formation (aircraft at ~6.0 km): stronger parallax = visible speed.
argv: bottom_km height_km (default 3.4 2.2 -> tops 5.6 km, ~400 m below the formation)."""
import unreal, sys
b = float(sys.argv[1]) if len(sys.argv) > 1 else 3.4
h = float(sys.argv[2]) if len(sys.argv) > 2 else 2.2
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
c = next(a for a in eas.get_all_level_actors() if isinstance(a, unreal.VolumetricCloud)).get_component_by_class(unreal.VolumetricCloudComponent)
c.modify()
unreal.log("[CloudLayer] before bottom %.2f height %.2f" % (c.get_editor_property("layer_bottom_altitude"), c.get_editor_property("layer_height")))
c.set_editor_property("layer_bottom_altitude", b); c.set_editor_property("layer_height", h)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
unreal.log("[CloudLayer] bottom %.2f km, tops %.2f km" % (b, b + h))
