"""Stop the joystick from flying the editor viewport camera (RawInput sends it as gamepad/trigger axes)."""
import unreal
cls = unreal.load_class(None, "/Script/UnrealEd.LevelEditorViewportSettings"); s = unreal.get_default_object(cls)
for name in ("bLevelEditorJoystickControls", "level_editor_joystick_controls"):
    try:
        unreal.log("[EdJoy] before %s=%s" % (name, s.get_editor_property(name)))
        s.set_editor_property(name, False)
        unreal.log("[EdJoy] %s=%s" % (name, s.get_editor_property(name)))
        break
    except Exception as e:
        unreal.log("[EdJoy] %s: %s" % (name, e))
try:
    s.save_config()
except Exception as e:
    unreal.log("[EdJoy] save_config: %s" % e)
# persist for this project (also read at editor start)
import os
ini = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_config_dir()) + "DefaultEditorPerProjectUserSettings.ini"
txt = open(ini, encoding="utf-8").read() if os.path.exists(ini) else ""
if "bLevelEditorJoystickControls" not in txt:
    with open(ini, "a", encoding="utf-8") as f:
        f.write("\n[/Script/UnrealEd.LevelEditorViewportSettings]\nbLevelEditorJoystickControls=False\n")
    unreal.log("[EdJoy] wrote " + ini)
