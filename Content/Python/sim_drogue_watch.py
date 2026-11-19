"""PIE test: optionally teleport the Mirage relative to the drogue (argv dx dy dz vy = probe target offset from drogue, Mirage fwd speed),
then log drogue offset/velocity, distance basket->eye and state every 0.25 s for 4 s."""
import unreal, sys, time
w = unreal.EditorLevelLibrary.get_game_world()
hose = [a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor) if "BP_RefuelHose" in a.get_class().get_name()][0]
pawn = unreal.GameplayStatics.get_player_pawn(w, 0)
comp = lambda a, n: [c for c in a.get_components_by_class(unreal.SceneComponent) if c.get_name() == n][0]
drg, probe, cam = comp(hose, "Drogue"), comp(pawn, "ProbeTip"), comp(pawn, "PilotCam")
if len(sys.argv) > 4:
    off = drg.get_world_location() + unreal.Vector(float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3])) - probe.get_world_location()
    pawn.set_actor_location(pawn.get_actor_location() + off, False, True)
    pawn.set_editor_property("Velocity", unreal.Vector(0, float(sys.argv[4]), 0))
st = {"t0": time.time(), "last": -1, "h": None}
def tick(dt):
    t = time.time() - st["t0"]
    if t - st["last"] >= 0.25:
        st["last"] = t
        d = drg.get_world_location(); p = probe.get_world_location(); e = cam.get_world_location()
        o = hose.get_editor_property("DrogueOff"); v = hose.get_editor_property("DrogueVel")
        unreal.log("[DrogueWatch t=%.2f] state=%s off=(%.0f,%.0f,%.0f) vel=(%.0f,%.0f,%.0f) |drogue-probe|=%.0f |drogue-eye|=%.0f msg=%s" % (
            t, hose.get_editor_property("State"), o.x, o.y, o.z, v.x, v.y, v.z, (d - p).length(), (d - e).length(), hose.get_editor_property("Msg")))
    if t > 4.0 and st["h"] is not None:
        unreal.unregister_slate_post_tick_callback(st["h"]); st["h"] = None
st["h"] = unreal.register_slate_post_tick_callback(tick)
