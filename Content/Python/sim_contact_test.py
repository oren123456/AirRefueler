"""PIE contact test. argv: dx dz vy [tag] = probe placed at drogue + (dx, -150, dz) cm, flown at vy cm/s (+Y = forward).
Trails the hose first (ExtendCount++), waits for READY, then logs every frame for 4 s: probe in basket coords,
drogue step |dP| per frame, drogue speed, state, msg. Summary line [Contact] at the end. Stops PIE."""
import unreal, time, sys, math
dx, dz, vy = (float(a) for a in sys.argv[1:4]) if len(sys.argv) > 3 else (0.0, 0.0, 120.0)
tag = sys.argv[4] if len(sys.argv) > 4 else ""
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if unreal.EditorLevelLibrary.get_game_world() is None:
    les.editor_request_begin_play()
log = lambda s: unreal.log("[Contact%s] %s" % (tag, s))
st = {"t0": None, "phase": 0, "tp": None, "prev": None, "maxstep": 0.0, "maxacc": 0.0, "pv": None, "maxv": 0.0, "states": [], "h": None, "n": 0}
def tick(dt):
    w = unreal.EditorLevelLibrary.get_game_world()
    if w is None: return
    if st["t0"] is None: st["t0"] = time.time()
    t = time.time() - st["t0"]
    hs = [a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor) if "BP_RefuelHose" in a.get_class().get_name()]
    pawn = unreal.GameplayStatics.get_player_pawn(w, 0)
    if not hs or pawn is None: return
    hose = hs[0]
    drg = [c for c in hose.get_components_by_class(unreal.SceneComponent) if c.get_name() == "Parachute"][0]
    probe = [c for c in pawn.get_components_by_class(unreal.SceneComponent) if c.get_name() == "ProbeTip"][0]
    S = hose.get_editor_property("State")
    if st["phase"] == 0 and t > 0.5:
        if S != 2:   # hose starts trailed now; only extend if it is stowed
            pawn.set_editor_property("ExtendCount", pawn.get_editor_property("ExtendCount") + 1)
        st["phase"] = 1
    elif st["phase"] == 1 and S == 2:
        st["phase"] = 2; st["tready"] = t
    elif st["phase"] == 2 and t > st["tready"] + 2.0:
        off = drg.get_world_location() + unreal.Vector(dx, -150.0, dz) - probe.get_world_location()
        pawn.set_actor_location(pawn.get_actor_location() + off, False, True)
        st["phase"] = 3; st["tp"] = t
    elif st["phase"] == 3:
        pawn.set_editor_property("Velocity", unreal.Vector(0, vy, 0))
        tt = t - st["tp"]
        P = drg.get_world_location(); pr = probe.get_world_location()
        loc = unreal.MathLibrary.inverse_transform_location(drg.get_world_transform(), pr)
        r = math.hypot(loc.y, loc.z)
        if st["prev"] is not None:
            step = (P - st["prev"]).length(); v = step / max(dt, 1e-3)
            st["maxv"] = max(st["maxv"], v)
            if st["pv"] is not None: st["maxacc"] = max(st["maxacc"], abs(v - st["pv"]) / max(dt, 1e-3))
            st["pv"] = v
            st["maxstep"] = max(st["maxstep"], step)
        st["prev"] = P
        if S not in st["states"]: st["states"].append(S)
        st["n"] += 1
        DP = hose.get_editor_property("DP"); pod = hose.get_actor_location()
        rot = unreal.MathLibrary.make_rot_from_x(pod - DP)
        bl = unreal.MathLibrary.inverse_transform_location(unreal.Transform(DP, rot, unreal.Vector(1, 1, 1)), pr)
        br = math.hypot(bl.y, bl.z); q = max(0.0, -49.5 - bl.x); wr = 5 + 0.3 * q + 0.02 * q * q
        dbg = "bp(x=%.1f r=%.1f pen1=%.1f) CL=%.0f pawnVel=%.0f actorVel=%.0f" % (bl.x, br, br + 4 - wr, hose.get_editor_property("CL"), pawn.get_editor_property("Velocity").y, pawn.get_velocity().y)
        if st["n"] % 3 == 0:
            log("t=%.2f S=%d probe(x=%.0f r=%.0f) drogue=(%.0f,%.0f,%.0f) %s msg=%s" % (tt, S, loc.x, r, P.x, P.y, P.z, dbg, hose.get_editor_property("Msg")[:30]))
        if tt > 4.0:
            log("SUMMARY dx=%s dz=%s vy=%s states=%s maxstep=%.1fcm maxspeed=%.0fcm/s maxaccel=%.0fcm/s2 final=%s" % (dx, dz, vy, st["states"], st["maxstep"], st["maxv"], st["maxacc"], hose.get_editor_property("Msg")))
            unreal.unregister_slate_post_tick_callback(st["h"]); les.editor_request_end_play()
st["h"] = unreal.register_slate_post_tick_callback(tick)
