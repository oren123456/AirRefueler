"""PIE: put one cloud puff on the formation's track 1.5 km ahead, photograph from the cockpit as it approaches,
while inside it, and after; log frame times. -> Saved/ClaudeShots/puff_test.txt"""
import unreal, time
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if unreal.EditorLevelLibrary.get_game_world() is None: les.editor_request_begin_play()
st = {"t0": None, "h": None, "out": [], "shots": [], "placed": False}
def comp(a, n): return [c for c in a.get_components_by_class(unreal.SceneComponent) if c.get_name() == n][0]
def tick(dt):
    try: _tick(dt)
    except Exception as e:
        unreal.log("[PuffTest] ERROR %s" % e); unreal.unregister_slate_post_tick_callback(st["h"]); les.editor_request_end_play()
def _tick(dt):
    w = unreal.EditorLevelLibrary.get_game_world()
    if w is None: return
    now = time.time()
    if st["t0"] is None: st["t0"] = now
    p = unreal.GameplayStatics.get_player_pawn(w, 0)
    puffs = unreal.GameplayStatics.get_all_actors_with_tag(w, "CloudPuff")
    if p is None or not puffs: return
    cam = comp(p, "PilotCam"); eye = cam.get_world_location()
    if not st["placed"] and now - st["t0"] > 2.0:
        a = puffs[0]; a.set_actor_scale3d(unreal.Vector(500, 500, 375))
        a.set_actor_location(eye + unreal.Vector(0, 150000, 0), False, True); st["puff"] = a; st["placed"] = True; st["tp"] = now
        p.set_editor_property("CamYaw", 0.0); p.set_editor_property("CamPitch", 0.0); cam.set_field_of_view(90.0)
    if st["placed"]:
        a = st["puff"]; dy = a.get_actor_location().y - eye.y
        st["out"].append("t=%.2f dt=%.1fms puff_dy=%.0f m" % (now - st["tp"], dt * 1000, dy / 100))
        for name, d in (("a_approach", 900), ("b_close", 350), ("c_inside", 0), ("d_after", -400)):
            if name not in st["shots"] and dy / 100 < d:
                unreal.SystemLibrary.execute_console_command(w, "HighResShot 1"); st["shots"].append(name); unreal.log("[PuffTest] " + name)
        if dy / 100 < -700 or now - st["tp"] > 25:
            open(unreal.Paths.project_saved_dir() + "ClaudeShots/puff_test.txt", "w").write("\n".join(st["out"]))
            unreal.unregister_slate_post_tick_callback(st["h"]); les.editor_request_end_play(); unreal.log("[PuffTest] done")
st["h"] = unreal.register_slate_post_tick_callback(tick)
