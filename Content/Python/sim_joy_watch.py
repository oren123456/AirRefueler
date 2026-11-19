"""Sample joystick key states in PIE for ~8 s via a Slate tick callback (lets the viewport take focus meanwhile)."""
import unreal, time
state = {"t0": time.time(), "last": 0, "h": None}
def tick(dt):
    t = time.time() - state["t0"]
    if t - state["last"] >= 1.0:
        state["last"] = t
        w = unreal.EditorLevelLibrary.get_game_world()
        pc = unreal.GameplayStatics.get_player_controller(w, 0) if w else None
        if pc:
            s = []
            for i in range(1, 6):
                k = unreal.Key(); k.import_text("GenericUSBController_Axis%d" % i)
                s.append("A%d=%.3f" % (i, pc.get_input_analog_key_state(k)))
            kw = unreal.Key(); kw.import_text("W")
            unreal.log("[JoyWatch t=%.0f] %s  W=%s" % (t, " ".join(s), pc.is_input_key_down(kw)))
    if t > 8 and state["h"] is not None:
        unreal.unregister_slate_post_tick_callback(state["h"]); state["h"] = None
w0 = unreal.EditorLevelLibrary.get_game_world()
pc0 = unreal.GameplayStatics.get_player_controller(w0, 0)
unreal.WidgetBlueprintLibrary.set_input_mode_game_only(pc0)
state["h"] = unreal.register_slate_post_tick_callback(tick)
