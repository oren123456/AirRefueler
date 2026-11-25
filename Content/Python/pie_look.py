"""PIE: set the pilot camera yaw/pitch (argv) and take a HighResShot."""
import unreal, sys
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
p = unreal.GameplayStatics.get_player_pawn(w, 0)
p.set_editor_property("CamYaw", float(sys.argv[1])); p.set_editor_property("CamPitch", float(sys.argv[2]) if len(sys.argv) > 2 else 0.0)
unreal.SystemLibrary.execute_console_command(w, "HighResShot 1")
unreal.log("[PieLook] yaw %s" % sys.argv[1])
