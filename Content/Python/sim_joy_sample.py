"""Log joystick key states + Enhanced Input action values in PIE."""
import unreal
w = unreal.EditorLevelLibrary.get_game_world()
pc = unreal.GameplayStatics.get_player_controller(w, 0)
s = []
for i in range(1, 6):
    k = unreal.Key(); k.import_text("GenericUSBController_Axis%d" % i)
    s.append("A%d=%.3f" % (i, pc.get_input_analog_key_state(k)))
out = " ".join(s)
try:
    lp = pc.get_local_player() if hasattr(pc, "get_local_player") else None
    sub = unreal.SubsystemBlueprintLibrary.get_local_player_subsystem(pc, unreal.EnhancedInputLocalPlayerSubsystem) if hasattr(unreal, "SubsystemBlueprintLibrary") else None
    out += " | sub=%s" % (sub.get_name() if sub else None)
    if sub:
        pi = sub.get_player_input()
        out += " pi=%s" % (pi.get_class().get_name() if pi else None)
        imc = unreal.load_asset("/Game/AirRefueler/Sim/Input/IMC_Joystick")
        out += " hasIMC=%s" % sub.has_mapping_context(imc)
        for i in range(1, 6):
            ia = unreal.load_asset("/Game/AirRefueler/Sim/Input/IA_JoyAxis%d" % i)
            try:
                v = pi.get_action_value(ia)
                out += " IA%d=%s" % (i, v.get_editor_property("value") if hasattr(v, "get_editor_property") else v)
            except Exception as e:
                out += " IA%d=ERR(%s)" % (i, str(e)[:60])
except Exception as e:
    out += " | EI err: %s" % e
unreal.log("[JoySample] " + out)
