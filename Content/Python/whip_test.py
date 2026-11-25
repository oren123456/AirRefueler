"""PIE: hose reel + whip. Lock in (KThr 40 + L), push in at 1 m/s for 2 s (reel keeps up), then 4 m/s
(reel takes up only 2.5 m/s -> slack -> HOSE WHIP disconnect). Logs slack/state; side-view HighResShot 0.35 s into the whip."""
import unreal, time, math
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if unreal.EditorLevelLibrary.get_game_world() is None: les.editor_request_begin_play()
log = lambda s: unreal.log("[Whip] " + s)
st = {"t0": None, "ph": 0, "h": None, "n": 0, "prev": None, "maxstep": 0.0}
V = unreal.Vector
def comp(a, n): return [c for c in a.get_components_by_class(unreal.SceneComponent) if c.get_name() == n][0]
def tick(dt):
    try: _tick(dt)
    except Exception as e:
        log("ERROR %s" % e); unreal.unregister_slate_post_tick_callback(st["h"]); les.editor_request_end_play()
def _tick(dt):
    w = unreal.EditorLevelLibrary.get_game_world()
    if w is None: return
    now = time.time()
    if st["t0"] is None: st["t0"] = now
    t = now - st["t0"]
    hs = [a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor) if "BP_RefuelHose" in a.get_class().get_name()]
    p = unreal.GameplayStatics.get_player_pawn(w, 0)
    if not hs or p is None: return
    h = hs[0]; drg = comp(h, "Parachute"); pr = comp(p, "ProbeTip"); cam = comp(p, "PilotCam"); S = h.get_editor_property("State")
    d = drg.get_world_location()
    loc = unreal.MathLibrary.inverse_transform_location(drg.get_world_transform(), pr.get_world_location()); r = math.hypot(loc.y, loc.z)
    info = lambda: "pyx=%.0f pyr=%.0f bpCX=%.0f bpCR=%.0f S=%d slack=%.0f WK=%.2f flowing=%s msg=%s" % (loc.x, r, h.get_editor_property("CX"), h.get_editor_property("CR"), S, h.get_editor_property("SL"), h.get_editor_property("WK"), h.get_editor_property("Flowing"), h.get_editor_property("Msg")[:70])
    if st["ph"] == 0 and t > 1.0 and S == 2:
        h.set_editor_property("TurbAmp", 0.0); h.set_editor_property("BowStrength", 0.0)
        off = d - drg.get_forward_vector() * 150.0 - pr.get_world_location()
        p.set_actor_location(p.get_actor_location() + off, False, True); st["dir"] = drg.get_forward_vector(); st["ph"] = 1
    elif st["ph"] == 1 and not (loc.x > -65 and r < 10):
        # home on the basket: steer the probe tip toward a point on the drogue axis just inside the mouth
        aimp = d - drg.get_forward_vector() * 55.0
        dv = aimp - pr.get_world_location(); L = max(dv.length(), 1.0)
        p.set_editor_property("Velocity", dv * (min(60.0, 2.0 * L) / L))
    elif st["ph"] == 1 and loc.x > -65 and r < 10:
        p.set_editor_property("LockCount", p.get_editor_property("LockCount") + 1); st["ph"] = 2; st["tl"] = t
    elif st["ph"] == 2 and t > st["tl"] + 0.5 and S != 3:
        log("lock refused, retrying: " + info()); st["ph"] = 1
    elif st["ph"] == 2 and t > st["tl"] + 0.5:
        log("locked: " + info()); st["ph"] = 3; st["tp"] = t
    elif st["ph"] == 3:
        p.set_editor_property("Velocity", V(0, 100, 0))
        if t > st["tp"] + 2.5: log("push 1 m/s for 2.5 s: " + info()); st["ph"] = 4; st["tf"] = t
    elif st["ph"] == 4:
        p.set_editor_property("Velocity", V(0, 400, 0))
        st["n"] += 1
        if st["n"] % 6 == 0: log("push 4 m/s t+%.2f: %s" % (t - st["tf"], info()))
        if S == 2: log("DISCONNECT after %.2f s: %s" % (t - st["tf"], info())); st["ph"] = 5; st["tw"] = t; st["cam"] = cam
    elif st["ph"] == 5:
        p.set_editor_property("Velocity", V(0, 0, 0))
        mid = (h.get_actor_location() + d) * 0.5
        cl = mid + V(-2600.0, 200.0, 150.0)
        cam.set_world_location(cl, False, True); lr = unreal.MathLibrary.find_look_at_rotation(cl, mid)
        p.set_editor_property("CamYaw", lr.yaw - 90.0); p.set_editor_property("CamPitch", lr.pitch); cam.set_field_of_view(50.0)
        if st["prev"] is not None: st["maxstep"] = max(st["maxstep"], (d - st["prev"]).length())
        st["prev"] = d
        if not st.get("shot") and t > st["tw"] + 0.35:
            unreal.SystemLibrary.execute_console_command(w, "HighResShot 1"); st["shot"] = True; log("shot during whip: " + info())
        if t > st["tw"] + 2.5:
            log("after whip: max drogue step %.1f cm/frame, %s" % (st["maxstep"], info()))
            h.set_editor_property("TurbAmp", 1.0); h.set_editor_property("BowStrength", 120.0)
            unreal.unregister_slate_post_tick_callback(st["h"]); les.editor_request_end_play()
    if t > 60: log("TIMEOUT ph=%d %s" % (st["ph"], info())); unreal.unregister_slate_post_tick_callback(st["h"]); les.editor_request_end_play()
st["h"] = unreal.register_slate_post_tick_callback(tick)
