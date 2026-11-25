"""PIE: log pawn Velocity and MPC_HUD values for a few seconds -> Saved/ClaudeShots/hud_test.txt"""
import unreal, time
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if unreal.EditorLevelLibrary.get_game_world() is None: les.editor_request_begin_play()
mpc = unreal.EditorAssetLibrary.load_asset("/Game/AirRefueler/Sim/HUD/MPC_HUD")
st = {"t0": None, "n": 0, "h": None, "out": []}
def tick(dt):
    try:
        w = unreal.EditorLevelLibrary.get_game_world()
        if w is None: return
        now = time.time()
        if st["t0"] is None: st["t0"] = now
        p = unreal.GameplayStatics.get_player_pawn(w, 0)
        if p and now - st["t0"] > 2.0 + st["n"] * 0.5:
            st["n"] += 1
            libs = [n for n in dir(unreal) if "MaterialLibrary" in n or "MaterialParameterCollection" in n]
            L = getattr(unreal, "KismetMaterialLibrary", None) or getattr(unreal, "MaterialLibrary", None)
            vals = [str(L.get_vector_parameter_value(w, mpc, n)) for n in ("D0", "D1", "Vel")] if L else []
            st["out"].append("libs=%s vel=%s vals=%s" % (libs, p.get_editor_property("Velocity"), vals))
        if st["n"] >= 4:
            open(unreal.Paths.project_saved_dir() + "ClaudeShots/hud_test.txt", "w").write("\n".join(st["out"]))
            unreal.unregister_slate_post_tick_callback(st["h"]); les.editor_request_end_play()
    except Exception as e:
        unreal.log("[HudTest] ERROR %s" % e); unreal.unregister_slate_post_tick_callback(st["h"]); les.editor_request_end_play()
st["h"] = unreal.register_slate_post_tick_callback(tick)
