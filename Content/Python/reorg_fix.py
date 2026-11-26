"""Finish the reorg: resave everything that references a redirector, delete the redirectors, save; report."""
import unreal, json
R = "/Game/AirRefueler"
eal = unreal.EditorAssetLibrary
ar = unreal.AssetRegistryHelpers.get_asset_registry()
opts = unreal.AssetRegistryDependencyOptions(include_soft_package_references=True, include_hard_package_references=True)
reds = [str(ad.package_name) for ad in ar.get_assets_by_path(R, recursive=True) if str(ad.asset_class_path.asset_name) == "ObjectRedirector"]
refs = set()
for r in reds:
    for x in ar.get_referencers(r, opts) or []:
        x = str(x)
        if x not in reds: refs.add(x)
resaved = []
for x in sorted(refs):
    if eal.load_asset(x) is not None:
        if eal.save_asset(x, only_if_is_dirty=False): resaved.append(x)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
left_refs = {}
deleted = []
for r in reds:
    rr = [str(x) for x in (ar.get_referencers(r, opts) or []) if str(x) not in reds]
    if rr: left_refs[r] = rr[:3]; continue
    if eal.delete_asset(r): deleted.append(r)
eal.save_directory(R, only_if_is_dirty=True, recursive=True)
m = json.load(open(r"D:/GitHub/AirRefueler/Saved/ClaudeShots/reorg_map.json")) if False else None
open(r"D:/GitHub/AirRefueler/Saved/ClaudeShots/reorg_fix.json", "w").write(json.dumps({"redirectors": len(reds), "resaved": len(resaved), "deleted": len(deleted), "still_referenced": left_refs}, indent=0))
