"""PIE, then two HighResShots from the cockpit 3 s apart (argv: gap seconds), then stop PIE."""
import unreal, time, sys
gap = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if unreal.EditorLevelLibrary.get_game_world() is None:
    les.editor_request_begin_play()
st = {"t0": None, "step": 0, "h": None}
def tick(dt):
    w = unreal.EditorLevelLibrary.get_game_world()
    if w is None: return
    if st["t0"] is None: st["t0"] = time.time()
    t = time.time() - st["t0"]
    if st["step"] == 0 and t > 3.0:
        unreal.SystemLibrary.execute_console_command(w, "HighResShot 1"); st["step"] = 1
    elif st["step"] == 1 and t > 3.0 + gap:
        unreal.SystemLibrary.execute_console_command(w, "HighResShot 1"); st["step"] = 2
    elif st["step"] == 2 and t > 4.5 + gap:
        unreal.unregister_slate_post_tick_callback(st["h"]); les.editor_request_end_play(); unreal.log("[TwoShots] done")
st["h"] = unreal.register_slate_post_tick_callback(tick)
