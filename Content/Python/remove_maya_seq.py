"""Delete the old Maya baked Level Sequence (RootNode_TrackSetNode) and any LevelSequenceActor that plays it."""
import unreal
eal = unreal.EditorAssetLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
log = lambda *x: unreal.log("[RemoveSeq] " + " ".join(str(v) for v in x))
seqs = [p for p in eal.list_assets("/Game/AirRefueler", recursive=True, include_folder=False)
        if str(eal.find_asset_data(p).asset_class_path.asset_name) == "LevelSequence"]
log("sequences:", seqs)
try:
    unreal.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
except Exception as e:
    log("close:", e)
for a in eas.get_all_level_actors():
    if isinstance(a, unreal.LevelSequenceActor):
        log("destroy actor", a.get_actor_label()); eas.destroy_actor(a)
for p in seqs:
    refs = unreal.EditorAssetLibrary.find_package_referencers_for_asset(p, False)
    log(p, "referencers:", refs)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(eal.load_asset(p))
    log("deleted" if eal.delete_asset(p) else "FAILED", p)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
log("done")
