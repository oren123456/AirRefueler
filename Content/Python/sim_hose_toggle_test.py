"""PIE test for the hose out/in toggle (E / joystick button 2 -> BP_MiragePawn.ExtendCount++).
Starts PIE if needed, then bumps ExtendCount at t=1 (expect trailing), t=4 (expect rewinding),
t=6 (expect trailing again) and logs State/HoseLen/Msg every 0.5 s for 8 s. Stops PIE at the end."""
import unreal, time
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if unreal.EditorLevelLibrary.get_game_world() is None:
    les.editor_request_begin_play()
st = {"t0": None, "last": -1.0, "bumps": [1.0, 4.0, 6.0], "h": None}
log = lambda s: unreal.log("[HoseToggle] " + s)
def tick(dt):
    w = unreal.EditorLevelLibrary.get_game_world()
    if w is None:
        return
    if st["t0"] is None:
        st["t0"] = time.time()
    t = time.time() - st["t0"]
    hose = [a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor) if "BP_RefuelHose" in a.get_class().get_name()]
    pawn = unreal.GameplayStatics.get_player_pawn(w, 0)
    if not hose or pawn is None:
        return
    hose = hose[0]
    if st["bumps"] and t >= st["bumps"][0]:
        st["bumps"].pop(0)
        n = pawn.get_editor_property("ExtendCount") + 1
        pawn.set_editor_property("ExtendCount", n)
        log("t=%.2f press -> ExtendCount=%d" % (t, n))
    if t - st["last"] >= 0.5:
        st["last"] = t
        log("t=%.2f state=%s hoselen=%.0f msg=%s" % (t, hose.get_editor_property("State"), hose.get_editor_property("HoseLen"), hose.get_editor_property("Msg")))
    if t > 8.0:
        unreal.unregister_slate_post_tick_callback(st["h"])
        les.editor_request_end_play()
        log("done")
st["h"] = unreal.register_slate_post_tick_callback(tick)
