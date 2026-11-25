"""PIE realism check: (A) 8 s drogue turbulence with the jet far away; (B) turbulence off, approach on the axis
from 6 m at 50 cm/s, log bow-wave displacement of the basket vs nose distance and whether it latches;
(C) pod lights: READY amber, push in -> green while fuel flows."""
import unreal, time, math
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if unreal.EditorLevelLibrary.get_game_world() is None: les.editor_request_begin_play()
log = lambda s: unreal.log("[Realism] " + s)
st = {"t0": None, "ph": 0, "h": None, "pts": [], "n": 0}
V = unreal.Vector
def comp(a, n): return [c for c in a.get_components_by_class(unreal.SceneComponent) if c.get_name() == n][0]
def tick(dt):
    try: _tick(dt)
    except Exception as e:
        log("ERROR %s" % e); unreal.unregister_slate_post_tick_callback(st["h"]); les.editor_request_end_play()
def lights(h): return "".join(n[0] for n in ("Red", "Amber", "Green") if comp(h, "Light" + n).is_visible()) or "-"
def _tick(dt):
    w = unreal.EditorLevelLibrary.get_game_world()
    if w is None: return
    now = time.time()
    if st["t0"] is None: st["t0"] = now
    t = now - st["t0"]
    hs = [a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor) if "BP_RefuelHose" in a.get_class().get_name()]
    p = unreal.GameplayStatics.get_player_pawn(w, 0)
    if not hs or p is None: return
    h = hs[0]; drg = comp(h, "Parachute"); pr = comp(p, "ProbeTip")
    d = drg.get_world_location(); S = h.get_editor_property("State")
    nose = p.get_actor_location() + V(0, 750, 30)
    if st["ph"] == 0 and t > 1.0:
        st["ph"] = 1; st["ta"] = t; log("A: turbulence, lights=%s S=%d" % (lights(h), S))
    elif st["ph"] == 1:
        st["pts"].append(d)
        if t > st["ta"] + 8.0:
            pts = st["pts"]; m = V(sum(q.x for q in pts) / len(pts), sum(q.y for q in pts) / len(pts), sum(q.z for q in pts) / len(pts))
            dx = max(q.x for q in pts) - min(q.x for q in pts); dy = max(q.y for q in pts) - min(q.y for q in pts); dz = max(q.z for q in pts) - min(q.z for q in pts)
            log("A: drogue peak-to-peak over 8 s: lateral %.0f cm, fore-aft %.0f cm, vertical %.0f cm" % (dx, dy, dz))
            h.set_editor_property("TurbAmp", 0.0); st["ph"] = 2; st["tb"] = t
    elif st["ph"] == 2 and t > st["tb"] + 4.0:
        st["d0"] = d
        off = d - drg.get_forward_vector() * 600.0 - pr.get_world_location()
        p.set_actor_location(p.get_actor_location() + off, False, True); st["ph"] = 3; st["tc"] = t; st["maxdisp"] = 0.0
        st["dir"] = drg.get_forward_vector()   # fly along the hose line (it slopes ~9 deg down)
    elif st["ph"] == 3:
        p.set_editor_property("Velocity", st["dir"] * 50.0)
        disp = d - st["d0"]; lat = math.hypot(disp.x, disp.z); st["maxdisp"] = max(st["maxdisp"], lat)
        st["n"] += 1
        if st["n"] % 15 == 0:
            loc = unreal.MathLibrary.inverse_transform_location(drg.get_world_transform(), pr.get_world_location())
            log("B: nose-drogue %.0f cm, basket pushed x=%+.0f z=%+.0f (lateral %.0f cm), probe x=%.0f r=%.0f S=%d lights=%s" % ((d - nose).length(), disp.x, disp.z, lat, loc.x, math.hypot(loc.y, loc.z), S, lights(h)))
        if S == 3:
            log("B: LATCHED, max bow displacement %.0f cm, lights=%s" % (st["maxdisp"], lights(h))); st["ph"] = 4; st["td"] = t
        elif t > st["tc"] + 16:
            log("B: no latch after 16 s, max bow displacement %.0f cm, msg=%s" % (st["maxdisp"], h.get_editor_property("Msg"))); st["ph"] = 6; st["te"] = t
    elif st["ph"] == 4:
        p.set_editor_property("Velocity", V(0, 100, 0)) if t < st["td"] + 3.0 else p.set_editor_property("Velocity", V(0, 0, 0))
        if t > st["td"] + 4.0:
            log("C: pushed in, flowing=%s lights=%s msg=%s" % (h.get_editor_property("Flowing"), lights(h), h.get_editor_property("Msg")[:50])); st["ph"] = 6; st["te"] = t
    elif st["ph"] == 6 and t > st["te"] + 0.5:
        h.set_editor_property("TurbAmp", 1.0)
        unreal.unregister_slate_post_tick_callback(st["h"]); les.editor_request_end_play(); log("done")
    if t > 60: log("TIMEOUT"); unreal.unregister_slate_post_tick_callback(st["h"]); les.editor_request_end_play()
st["h"] = unreal.register_slate_post_tick_callback(tick)
