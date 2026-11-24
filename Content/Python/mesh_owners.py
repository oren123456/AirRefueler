"""Map every StaticMesh asset under /Game to the level root group(s) that use it -> Saved/ClaudeShots/mesh_owners.json"""
import unreal, json
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = eas.get_all_level_actors()
kids = {}
for a in actors:
    p = a.get_attach_parent_actor()
    if p: kids.setdefault(p.get_path_name(), []).append(a)
roots = [a for a in actors if not a.get_attach_parent_actor()]
rn = [a for a in roots if a.get_actor_label() == "RootNode"]
if rn:
    roots = [a for a in roots if a is not rn[0]] + kids.get(rn[0].get_path_name(), [])
def desc(a):
    out = [a]
    for k in kids.get(a.get_path_name(), []): out += desc(k)
    return out
use = {}
for r in roots:
    for a in desc(r):
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            sm = c.get_editor_property("static_mesh")
            if sm: use.setdefault(sm.get_path_name().split(".")[0], set()).add(r.get_actor_label())
# blueprint components (Sim BPs)
for bp in ("/Game/AirRefueler/Sim/BP_MiragePawn", "/Game/AirRefueler/Sim/BP_RefuelHose"):
    for dep in unreal.EditorAssetLibrary.find_package_referencers_for_asset(bp, False): pass
ar = unreal.AssetRegistryHelpers.get_asset_registry()
allsm = ar.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "StaticMesh"), False)
rows = {}
for ad in allsm:
    p = str(ad.package_name)
    if not p.startswith("/Game"): continue
    refs = [str(x) for x in ar.get_referencers(ad.package_name, unreal.AssetRegistryDependencyOptions())] if hasattr(ar, "get_referencers") else []
    rows[p] = {"roots": sorted(use.get(p, [])), "refs": refs}
path = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()) + "ClaudeShots/mesh_owners.json"
open(path, "w").write(json.dumps(rows, indent=0))
unreal.log("[MeshOwners] %d meshes -> %s" % (len(rows), path))
