"""PIE start check: state, hose length, pod-drogue distance every 0.25 s for 3 s, HighResShot at 1.5 s."""
import unreal, time
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if unreal.EditorLevelLibrary.get_game_world() is None: les.editor_request_begin_play()
st = {"t0": None, "last": -1, "shot": False, "h": None}
log = lambda s: unreal.log("[StartCheck] " + s)
def tick(dt):
    w = unreal.EditorLevelLibrary.get_game_world()
    if w is None: return
    if st["t0"] is None: st["t0"] = time.time()
    t = time.time() - st["t0"]
    hs = [a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor) if "BP_RefuelHose" in a.get_class().get_name()]
    if not hs: return
    h = hs[0]; d = [c for c in h.get_components_by_class(unreal.SceneComponent) if c.get_name() == "Parachute"][0]
    if t - st["last"] >= 0.25:
        st["last"] = t
        log("t=%.2f state=%s hoselen=%.0f dist=%.0f msg=%s" % (t, h.get_editor_property("State"), h.get_editor_property("HoseLen"), (d.get_world_location() - h.get_actor_location()).length(), h.get_editor_property("Msg")[:40]))
    if not st["shot"] and t > 1.5:
        unreal.SystemLibrary.execute_console_command(w, "HighResShot 1"); st["shot"] = True
    if t > 3.0:
        unreal.unregister_slate_post_tick_callback(st["h"]); les.editor_request_end_play()
st["h"] = unreal.register_slate_post_tick_callback(tick)
