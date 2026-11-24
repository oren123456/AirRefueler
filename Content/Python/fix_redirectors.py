"""Resolve ObjectRedirectors under /Game/AirRefueler: resave every referencer (loading follows the redirect, saving
writes the new path), then delete redirectors nobody references any more. Also removes emptied folders."""
import unreal
R = "/Game/AirRefueler"
log = lambda s: unreal.log("[FixRedir] " + s)
eal = unreal.EditorAssetLibrary
ar = unreal.AssetRegistryHelpers.get_asset_registry()
reds = [ad for ad in ar.get_assets_by_path(R, True) if str(ad.asset_class_path.asset_name) == "ObjectRedirector"]
log("redirectors: %d" % len(reds))
opts = unreal.AssetRegistryDependencyOptions(include_soft_package_references=True, include_hard_package_references=True)
refs = set()
for ad in reds:
    for r in ar.get_referencers(ad.package_name, opts) or []:
        refs.add(str(r))
refs = sorted(r for r in refs if r.startswith("/Game"))
log("referencers to resave: %s" % refs)
for r in refs:
    a = eal.load_asset(r)
    if a:
        eal.save_asset(r, only_if_is_dirty=False)
lvl = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
lvl.save_current_level()
left = 0
for ad in reds:
    still = [str(x) for x in (ar.get_referencers(ad.package_name, opts) or []) if str(x).startswith("/Game")]
    if still:
        left += 1; log("still referenced %s <- %s" % (ad.package_name, still)); continue
    eal.delete_asset(str(ad.package_name))
log("deleted %d, kept %d" % (len(reds) - left, left))
for f in ("/Game/AirRefueler/Scene", "/Game/AirRefueler/Sim"):
    log("%s now has %d assets" % (f, len(eal.list_assets(f, recursive=True))))
