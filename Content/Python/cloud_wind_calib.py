"""Calibrate cloud wind speed: set Layout_WindControls to (0, -W, 0, 1), PIE, look down 55 deg,
two HighResShots ~2 s apart (game times logged). argv: W (default 1)."""
import unreal, time, sys
W = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
mel = unreal.MaterialEditingLibrary
mi = unreal.load_asset("/Game/AirRefueler/Maps/MI_VolumetricCloud_Refuel")
mel.set_material_instance_vector_parameter_value(mi, "Layout_WindControls", unreal.LinearColor(0.0, -W, 0.0, 1.0))
mel.update_material_instance(mi)
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if unreal.EditorLevelLibrary.get_game_world() is None:
    les.editor_request_begin_play()
log = lambda s: unreal.log("[WindCalib] " + s)
st = {"t0": None, "step": 0, "h": None}
def tick(dt):
    w = unreal.EditorLevelLibrary.get_game_world()
    if w is None: return
    if st["t0"] is None: st["t0"] = time.time()
    t = time.time() - st["t0"]
    pc = unreal.GameplayStatics.get_player_controller(w, 0)
    if pc is None: return
    if st["step"] == 0 and t > 2.0:
        pc.set_control_rotation(unreal.Rotator(roll=0.0, pitch=-55.0, yaw=90.0)); st["step"] = 1
    elif st["step"] == 1 and t > 4.0:
        unreal.SystemLibrary.execute_console_command(w, "HighResShot 1"); log("shot1 game=%.3f" % unreal.GameplayStatics.get_time_seconds(w)); st["step"] = 2
    elif st["step"] == 2 and t > 6.0:
        unreal.SystemLibrary.execute_console_command(w, "HighResShot 1"); log("shot2 game=%.3f" % unreal.GameplayStatics.get_time_seconds(w)); st["step"] = 3
    elif st["step"] == 3 and t > 7.5:
        unreal.unregister_slate_post_tick_callback(st["h"]); les.editor_request_end_play(); log("done W=%s" % W)
st["h"] = unreal.register_slate_post_tick_callback(tick)
