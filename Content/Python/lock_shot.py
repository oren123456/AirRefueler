"""PIE: lock in (KThr 40 + L), wait 1.5 s, log probe depth in the basket, switch the view to a side camera next to
the drogue and take a HighResShot."""
import unreal, time, math
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if unreal.EditorLevelLibrary.get_game_world() is None: les.editor_request_begin_play()
st = {"t0": None, "ph": 0, "h": None}
log = lambda s: unreal.log("[LockShot] " + s)
def tick(dt):
    try:
        _tick(dt)
    except Exception as e:
        log("ERROR %s" % e); unreal.unregister_slate_post_tick_callback(st["h"]); les.editor_request_end_play()
def _tick(dt):
    w = unreal.EditorLevelLibrary.get_game_world()
    if w is None: return
    if st["t0"] is None: st["t0"] = time.time()
    t = time.time() - st["t0"]
    hs = [a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor) if "BP_RefuelHose" in a.get_class().get_name()]
    p = unreal.GameplayStatics.get_player_pawn(w, 0)
    if not hs or p is None: return
    h = hs[0]; drg = [c for c in h.get_components_by_class(unreal.SceneComponent) if c.get_name() == "Parachute"][0]
    pr = [c for c in p.get_components_by_class(unreal.SceneComponent) if c.get_name() == "ProbeTip"][0]
    loc = unreal.MathLibrary.inverse_transform_location(drg.get_world_transform(), pr.get_world_location()); r = math.hypot(loc.y, loc.z)
    S = h.get_editor_property("State")
    if st["ph"] == 0 and t > 1.0 and S == 2:
        off = drg.get_world_location() - drg.get_forward_vector() * 150.0 - pr.get_world_location()
        p.set_actor_location(p.get_actor_location() + off, False, True); p.set_editor_property("KThr", 40.0); st["ph"] = 1
    elif st["ph"] == 1 and loc.x > -70 and r < 12:
        p.set_editor_property("LockCount", p.get_editor_property("LockCount") + 1); st["ph"] = 2; st["tl"] = t
    elif st["ph"] == 2 and t > st["tl"] + 1.5:
        log("locked S=%d probe tip x=%.1f cm (throat -49.5, hub 0) r=%.1f" % (S, loc.x, r))
        st["cam"] = [c for c in p.get_components_by_class(unreal.SceneComponent) if c.get_name() == "PilotCam"][0]
        st["ph"] = 3; st["tc"] = t
    if st["ph"] in (3, 4):
        d = drg.get_world_location(); cl = d + unreal.Vector(-170.0, -60.0, 35.0)
        st["cam"].set_world_location(cl, False, True)
        lr = unreal.MathLibrary.find_look_at_rotation(cl, d + unreal.Vector(0, -40, 0))
        p.set_editor_property("CamYaw", lr.yaw - 90.0); p.set_editor_property("CamPitch", lr.pitch)
    if st["ph"] == 3 and t > st["tc"] + 0.4:
        unreal.SystemLibrary.execute_console_command(w, "HighResShot 1"); st["ph"] = 4; st["ts"] = t
    elif st["ph"] == 4 and t > st["ts"] + 1.0:
        unreal.unregister_slate_post_tick_callback(st["h"]); les.editor_request_end_play(); log("done")
    if t > 30:
        unreal.unregister_slate_post_tick_callback(st["h"]); les.editor_request_end_play(); log("timeout ph=%d" % st["ph"])
st["h"] = unreal.register_slate_post_tick_callback(tick)
