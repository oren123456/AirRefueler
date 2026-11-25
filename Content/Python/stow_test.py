"""PIE: rewind the hose (E), log HoseLen / drogue position relative to the pod mouth, then photograph the stowed
basket from behind-left and from the side. Output Saved/ClaudeShots/stow_test.txt"""
import unreal, time, math
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if unreal.EditorLevelLibrary.get_game_world() is None: les.editor_request_begin_play()
V = unreal.Vector
st = {"t0": None, "h": None, "out": [], "phase": 0, "tn": 0}
def comp(a, n): return [c for c in a.get_components_by_class(unreal.SceneComponent) if c.get_name() == n][0]
def tick(dt):
    try: _tick(dt)
    except Exception as e:
        unreal.log("[Stow] ERROR %s" % e); unreal.unregister_slate_post_tick_callback(st["h"]); les.editor_request_end_play()
def _tick(dt):
    w = unreal.EditorLevelLibrary.get_game_world()
    if w is None: return
    now = time.time()
    if st["t0"] is None: st["t0"] = now
    hs = [a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor) if "BP_RefuelHose" in a.get_class().get_name()]
    p = unreal.GameplayStatics.get_player_pawn(w, 0)
    if not hs or p is None: return
    h = hs[0]; drg = comp(h, "Parachute"); cam = comp(p, "PilotCam"); pod = h.get_actor_location()
    S = h.get_editor_property("State"); hl = h.get_editor_property("HoseLen"); d = drg.get_world_location() - pod
    sc = drg.get_editor_property("relative_scale3d")
    if st["phase"] == 0 and now - st["t0"] > 2.0:
        p.set_editor_property("ExtendCount", p.get_editor_property("ExtendCount") + 1); st["phase"] = 1; st["tr"] = now
    if st["phase"] >= 1 and (not st["out"] or now - st["tl"] > 0.5):
        st["tl"] = now
        st["out"].append("t=%5.1f S=%d HoseLen=%7.1f drg-pod=(%6.1f,%7.1f,%6.1f) rot=%s scale=%.2f" % (now - st["tr"], S, hl, d.x, d.y, d.z, drg.get_world_rotation(), sc.y))
    if st["phase"] == 1 and S == 0 and abs(hl + 76) < 2: st["phase"] = 2; st["tn"] = now + 2.0
    if st["phase"] >= 2:
        for c in [cam]:
            tgt = pod + V(0, -20, -5)
            cl = pod + (V(-260, -420, -60) if st["phase"] < 4 else V(-330, -40, -10))
            cam.set_world_location(cl, False, True)
            r = unreal.MathLibrary.find_look_at_rotation(cl, tgt)
            p.set_editor_property("CamYaw", r.yaw - 90.0); p.set_editor_property("CamPitch", r.pitch); cam.set_field_of_view(30.0)
        if now > st["tn"]:
            if st["phase"] in (2, 4):
                unreal.SystemLibrary.execute_console_command(w, "HighResShot 2"); st["phase"] += 1; st["tn"] = now + 2.0
            elif st["phase"] == 3: st["phase"] = 4; st["tn"] = now + 1.5
            else:
                open(unreal.Paths.project_saved_dir() + "ClaudeShots/stow_test.txt", "w").write("\n".join(st["out"]))
                unreal.unregister_slate_post_tick_callback(st["h"]); les.editor_request_end_play(); unreal.log("[Stow] done")
    if now - st["t0"] > 60:
        open(unreal.Paths.project_saved_dir() + "ClaudeShots/stow_test.txt", "w").write("\n".join(st["out"] + ["TIMEOUT"]))
        unreal.unregister_slate_post_tick_callback(st["h"]); les.editor_request_end_play()
st["h"] = unreal.register_slate_post_tick_callback(tick)
