"""PIE: manual lock (L). Probe placed 150 cm behind the drogue on its axis, flown in at 30 cm/s (below auto-latch).
Press L at +0.5 s (out of range), again once inside (x>-75, r<12), and again 1.5 s later (unlock)."""
import unreal, time, math
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if unreal.EditorLevelLibrary.get_game_world() is None: les.editor_request_begin_play()
st = {"t0": None, "ph": 0, "h": None, "n": 0}
log = lambda s: unreal.log("[LockTest] " + s)
def press(p): p.set_editor_property("LockCount", p.get_editor_property("LockCount") + 1)
def tick(dt):
    w = unreal.EditorLevelLibrary.get_game_world()
    if w is None: return
    if st["t0"] is None: st["t0"] = time.time()
    t = time.time() - st["t0"]
    hs = [a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor) if "BP_RefuelHose" in a.get_class().get_name()]
    p = unreal.GameplayStatics.get_player_pawn(w, 0)
    if not hs or p is None: return
    h = hs[0]; drg = [c for c in h.get_components_by_class(unreal.SceneComponent) if c.get_name() == "Parachute"][0]
    pr = [c for c in p.get_components_by_class(unreal.SceneComponent) if c.get_name() == "ProbeTip"][0]
    S = h.get_editor_property("State")
    loc = unreal.MathLibrary.inverse_transform_location(drg.get_world_transform(), pr.get_world_location()); r = math.hypot(loc.y, loc.z)
    if st["ph"] == 0 and t > 1.0 and S == 2:
        fwd = drg.get_forward_vector()
        off = drg.get_world_location() - fwd * 150.0 - pr.get_world_location()
        p.set_actor_location(p.get_actor_location() + off, False, True); st["ph"] = 1; st["tp"] = t
    elif st["ph"] >= 1:
        p.set_editor_property("Velocity", unreal.Vector(0, 30, 0))
        tt = t - st["tp"]
        if st["ph"] == 1 and tt > 0.5: press(p); st["ph"] = 2; log("PRESS L (early) x=%.0f r=%.0f" % (loc.x, r))
        elif st["ph"] == 2 and loc.x > -75 and r < 12: press(p); st["ph"] = 3; st["tl"] = tt; log("PRESS L (inside) x=%.0f r=%.0f" % (loc.x, r))
        elif st["ph"] == 3 and tt > st["tl"] + 1.5: press(p); st["ph"] = 4; st["tu"] = tt; log("PRESS L (unlock)")
        st["n"] += 1
        if st["n"] % 6 == 0 or st["ph"] in (2, 3) and st["n"] % 2 == 0:
            log("t=%.2f S=%d x=%.0f r=%.0f msg=%s" % (tt, S, loc.x, r, h.get_editor_property("Msg")[:70]))
        if tt > 12 or (st["ph"] == 4 and tt > st["tu"] + 1.0):
            log("END S=%d msg=%s" % (S, h.get_editor_property("Msg")))
            unreal.unregister_slate_post_tick_callback(st["h"]); les.editor_request_end_play()
st["h"] = unreal.register_slate_post_tick_callback(tick)
