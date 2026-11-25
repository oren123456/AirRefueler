"""PIE: lock stops the jet, envelope auto-unlocks. argv: side|back|fwd.
Approach on the keyboard throttle (KThr 40 cm/s), press L inside the basket, check speed+throttle drop to 0 and stay
there for 1 s, then drive out of the envelope (side: X 300 cm/s, back: Y -300, fwd: Y +400) until it unlocks;
logs drogue step per frame and whether it re-latches."""
import unreal, time, math, sys
mode = sys.argv[1] if len(sys.argv) > 1 else "side"
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if unreal.EditorLevelLibrary.get_game_world() is None: les.editor_request_begin_play()
st = {"t0": None, "ph": 0, "h": None, "n": 0, "prev": None, "maxstep": 0.0, "states": []}
log = lambda s: unreal.log("[Env-%s] %s" % (mode, s))
MOVE = {"side": unreal.Vector(300, 0, 0), "back": unreal.Vector(0, -300, 0), "fwd": unreal.Vector(0, 400, 0)}[mode]
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
    S = h.get_editor_property("State"); v = p.get_editor_property("Velocity"); k = p.get_editor_property("KThr")
    loc = unreal.MathLibrary.inverse_transform_location(drg.get_world_transform(), pr.get_world_location()); r = math.hypot(loc.y, loc.z)
    P = drg.get_world_location()
    if st["prev"] is not None and st["ph"] >= 4: st["maxstep"] = max(st["maxstep"], (P - st["prev"]).length())
    st["prev"] = P
    if S not in st["states"]: st["states"].append(S)
    if st["ph"] == 0 and t > 1.0 and S == 2:
        off = P - drg.get_forward_vector() * 150.0 - pr.get_world_location()
        p.set_actor_location(p.get_actor_location() + off, False, True); p.set_editor_property("KThr", 40.0); st["ph"] = 1; st["tp"] = t
    elif st["ph"] == 1 and loc.x > -70 and r < 12:
        p.set_editor_property("LockCount", p.get_editor_property("LockCount") + 1); st["ph"] = 2; st["tl"] = t
        log("PRESS L x=%.0f r=%.0f vel.y=%.0f KThr=%.0f" % (loc.x, r, v.y, k))
    elif st["ph"] == 2 and t > st["tl"] + 0.1:
        log("after lock: S=%d vel=(%.0f,%.0f,%.0f) KThr=%.0f msg=%s" % (S, v.x, v.y, v.z, k, h.get_editor_property("Msg")[:60])); st["ph"] = 3
    elif st["ph"] == 3 and t > st["tl"] + 1.1:
        log("hold 1 s: S=%d vel=(%.0f,%.0f,%.0f) KThr=%.0f" % (S, v.x, v.y, v.z, k)); st["ph"] = 4; st["tm"] = t
    elif st["ph"] == 4:
        p.set_editor_property("Velocity", MOVE)
        if S == 2:
            log("AUTO-UNLOCK after %.2f s: msg=%s" % (t - st["tm"], h.get_editor_property("Msg"))); st["ph"] = 5; st["tu"] = t
    elif st["ph"] == 5:
        p.set_editor_property("Velocity", unreal.Vector(0, 0, 0))
        if t > st["tu"] + 1.5:
            log("SUMMARY states=%s relatched=%s maxstep=%.1fcm final=%s" % (st["states"], S == 3, st["maxstep"], h.get_editor_property("Msg")))
            unreal.unregister_slate_post_tick_callback(st["h"]); les.editor_request_end_play()
    if t > 30:
        log("TIMEOUT ph=%d S=%d" % (st["ph"], S)); unreal.unregister_slate_post_tick_callback(st["h"]); les.editor_request_end_play()
st["h"] = unreal.register_slate_post_tick_callback(tick)
