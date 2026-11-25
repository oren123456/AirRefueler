"""argv: 'save' -> save BP_CockpitAudio + log compile status; 'play' -> start PIE; 'dump' -> dump active sounds of the PIE
world to the log; 'stop' -> end PIE."""
import unreal, sys
a = sys.argv[1] if len(sys.argv) > 1 else "save"
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if a == "save":
    bp = unreal.load_asset("/Game/AirRefueler/Sim/Audio/BP_CockpitAudio")
    unreal.BlueprintEditorLibrary.compile_blueprint(bp); unreal.EditorAssetLibrary.save_loaded_asset(bp)
    unreal.log("[AudioCheck] status %s" % bp.get_editor_property("status"))
elif a == "play":
    les.editor_play_simulate() if False else les.editor_request_begin_play()
elif a == "dump":
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    unreal.SystemLibrary.execute_console_command(w, "au.DumpActiveSounds")
    acts = [x for x in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor) if x.get_class().get_name().startswith("BP_CockpitAudio")]
    for x in acts:
        for c in x.get_components_by_class(unreal.AudioComponent):
            unreal.log("[AudioCheck] %s playing=%s vol=%.2f" % (c.get_name(), c.is_playing(), c.volume_multiplier))
        unreal.log("[AudioCheck] N=%.3f W=%.3f LastSt=%s T=%.1f Ann=%.1f GF=%.2f" % (x.get_editor_property("N"), x.get_editor_property("W"), x.get_editor_property("LastSt"), x.get_editor_property("T"), x.get_editor_property("Ann"), x.get_editor_property("GF")))
    unreal.log("[AudioCheck] actors %d" % len(acts))
elif a == "stop":
    les.editor_request_end_play()
