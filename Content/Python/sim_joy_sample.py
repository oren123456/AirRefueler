"""Log current GenericUSBController axis/button values in PIE."""
import unreal
w = unreal.EditorLevelLibrary.get_game_world()
pc = unreal.GameplayStatics.get_player_controller(w, 0)
s = []
for i in range(1, 13):
    k = unreal.Key(); k.import_text("GenericUSBController_Axis%d" % i)
    s.append("A%d=%.3f" % (i, pc.get_input_analog_key_state(k)))
b = []
for i in range(1, 13):
    k = unreal.Key(); k.import_text("GenericUSBController_Button%d" % i)
    if pc.is_input_key_down(k): b.append(i)
unreal.log("[JoySample] " + " ".join(s) + " buttons_down=" + str(b))
