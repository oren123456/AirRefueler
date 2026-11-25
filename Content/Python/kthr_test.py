"""PIE: keyboard throttle check. Sets BP_MiragePawn.KThr = 100 cm/s (= 4 x Up arrow) and logs forward speed for 5 s."""
import unreal, time
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if unreal.EditorLevelLibrary.get_game_world() is None: les.editor_request_begin_play()
st = {"t0": None, "last": -1, "set": False, "h": None}
log = lambda s: unreal.log("[KThr] " + s)
def tick(dt):
    w = unreal.EditorLevelLibrary.get_game_world()
    if w is None: return
    if st["t0"] is None: st["t0"] = time.time()
    t = time.time() - st["t0"]
    p = unreal.GameplayStatics.get_player_pawn(w, 0)
    if p is None: return
    if not st["set"] and t > 0.5:
        p.set_editor_property("KThr", 100.0); st["set"] = True
    if t - st["last"] >= 0.5:
        st["last"] = t; log("t=%.1f KThr=%.0f vel.y=%.0f cm/s" % (t, p.get_editor_property("KThr"), p.get_editor_property("Velocity").y))
    if t > 5.0:
        unreal.unregister_slate_post_tick_callback(st["h"]); les.editor_request_end_play()
st["h"] = unreal.register_slate_post_tick_callback(tick)
