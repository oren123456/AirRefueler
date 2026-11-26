"""Delete textures under /Game/AirRefueler that nothing references (registry referencers empty) and that the
level does not reach. Writes Saved/ClaudeShots/tex_delete.json."""
import unreal, json
ar = unreal.AssetRegistryHelpers.get_asset_registry(); eal = unreal.EditorAssetLibrary
R = "/Game/AirRefueler"
opts = unreal.AssetRegistryDependencyOptions(include_soft_package_references=True, include_hard_package_references=True)
used = set(); todo = [R + "/Maps/L_RefuelScene"]
while todo:
    p = todo.pop()
    if p in used: continue
    used.add(p)
    for d in ar.get_dependencies(p, opts) or []:
        d = str(d)
        if d.startswith("/Game/") and d not in used: todo.append(d)
cand = [str(ad.package_name) for ad in ar.get_assets_by_path(R, recursive=True) if str(ad.asset_class_path.asset_name).startswith("Texture")]
deleted, kept = [], []
for p in cand:
    refs = [str(x) for x in (ar.get_referencers(p, opts) or [])]
    if p in used or refs:
        if p not in used: kept.append([p, refs[:3]])
        continue
    if eal.delete_asset(p): deleted.append(p)
eal.save_directory(R, only_if_is_dirty=True, recursive=True)
left = [str(ad.package_name) for ad in ar.get_assets_by_path(R + "/Textures", recursive=True)]
open(r"D:/GitHub/AirRefueler/Saved/ClaudeShots/tex_delete.json", "w").write(json.dumps({"deleted": [p.replace(R + "/", "") for p in deleted], "kept_unused_but_referenced": kept, "left_in_Textures": left}, indent=0))
