"""PIE: probe parked deep in the basket (tip 15 cm behind the hub, stopped), then L -> must lock."""
import unreal, time, math
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if unreal.EditorLevelLibrary.get_game_world() is None: les.editor_request_begin_play()
log = lambda s: unreal.log("[DeepLock] " + s)
st = {"t0": None, "ph": 0, "h": None}
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
    h = hs[0]; drg = comp(h, "Parachute"); pr = comp(p, "ProbeTip"); S = h.get_editor_property("State")
    loc = unreal.MathLibrary.inverse_transform_location(drg.get_world_transform(), pr.get_world_location()); r = math.hypot(loc.y, loc.z)
    if st["ph"] == 0 and t > 0.5:
        h.set_editor_property("TurbAmp", 0.0); h.set_editor_property("BowStrength", 0.0); st["ph"] = 1
    elif st["ph"] == 1 and t > 3.5:
        off = drg.get_world_location() - drg.get_forward_vector() * 15.0 - pr.get_world_location()
        p.set_actor_location(p.get_actor_location() + off, False, True); p.set_editor_property("Velocity", unreal.Vector(0, 0, 0)); st["ph"] = 2; st["tp"] = t
    elif st["ph"] == 2 and t > st["tp"] + 0.6:
        log("parked: S=%d tip x=%.0f r=%.0f msg=%s" % (S, loc.x, r, h.get_editor_property("Msg")[:60]))
        p.set_editor_property("LockCount", p.get_editor_property("LockCount") + 1); st["ph"] = 3; st["tl"] = t
    elif st["ph"] == 3 and t > st["tl"] + 0.5:
        log("after L: S=%d msg=%s" % (S, h.get_editor_property("Msg")))
        h.set_editor_property("TurbAmp", 1.0); h.set_editor_property("BowStrength", 120.0)
        unreal.unregister_slate_post_tick_callback(st["h"]); les.editor_request_end_play()
st["h"] = unreal.register_slate_post_tick_callback(tick)
