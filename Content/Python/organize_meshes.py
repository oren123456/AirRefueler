"""Sort every StaticMesh under /Game/AirRefueler into per-component folders (references fixed, redirectors cleaned).
  Aircraft/B767 (+_Unused)   Aircraft/Mirage (+_Unused)   Aircraft/Su30   Drogue (+_Unused)   _Unused/Misc
Used = referenced by a level actor (by level root group). Unused meshes are classified by their original Maya
group (Saved/ClaudeShots/dump.json, taken before the Su-30/pod removals). argv[1] == 'go' moves, else dry run."""
import unreal, json, sys, collections
GO = len(sys.argv) > 1 and sys.argv[1] == "go"
R = "/Game/AirRefueler"
log = lambda s: unreal.log("[Organize] " + s)
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()) + "ClaudeShots/"
# ---- live usage by level root group
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
acts = eas.get_all_level_actors()
kids = collections.defaultdict(list)
for a in acts:
    p = a.get_attach_parent_actor()
    if p: kids[p.get_path_name()].append(a)
roots = [a for a in acts if not a.get_attach_parent_actor()]
rn = [a for a in roots if a.get_actor_label() == "RootNode"]
if rn: roots = [a for a in roots if a is not rn[0]] + kids[rn[0].get_path_name()]
def desc(a):
    out = [a]
    for k in kids[a.get_path_name()]: out += desc(k)
    return out
ROOT_DIR = {"Boing_Ctrl": "Aircraft/B767", "SimPlayer_Mirage": "Aircraft/Mirage", "SimHose_LeftPod": "Drogue"}
used = {}
for r in roots:
    for a in desc(r):
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            sm = c.get_editor_property("static_mesh")
            if sm: used.setdefault(sm.get_path_name().split(".")[0], set()).add(ROOT_DIR.get(r.get_actor_label(), "?" + r.get_actor_label()))
# ---- original Maya group for unused meshes
dump = json.load(open(saved + "dump.json"))
par = {x["label"]: x["parent"] for x in dump}
def top(l):
    while par.get(l) not in (None, "RootNode"): l = par[l]
    return l
orig = {R + "/Scene/" + x["mesh"]: top(x["label"]) for x in dump if x["mesh"]}
def unused_dir(p, name):
    g = orig.get(p, "")
    if name.startswith("SM_Su30") or g in ("suchoi_ConstGrp", "NozzleL", "Suchoi_Ctrl"): return "Aircraft/Su30"
    if name.startswith("SM_Mirage") or g == "Mirage_2000N": return "Aircraft/Mirage/_Unused"
    if g.startswith("Center_Pod_Drouge") or g == "group18": return "Drogue/_Unused"
    if g in ("pod1", "pod2", "Boing_Ctrl", "bo_767") or g.startswith("IMAN_ID") or any(g.startswith(k) for k in (
            "DM1601354", "B767_", "767_", "36T-", "36M_", "ANT-GPS", "TCAS", "A947", "UHF_", "TMP_")):
        return "Aircraft/B767/_Unused"
    return "_Unused/Misc"
ar = unreal.AssetRegistryHelpers.get_asset_registry()
plan = []
for ad in ar.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "StaticMesh"), False):
    p = str(ad.package_name)
    if not p.startswith(R + "/"): continue
    name = p.rsplit("/", 1)[1]
    u = used.get(p)
    if u and len(u) == 1 and not next(iter(u)).startswith("?"): d = next(iter(u))
    elif u: log("WARN %s used by %s -> left in place" % (p, sorted(u))); continue
    else: d = unused_dir(p, name)
    dst = R + "/" + d
    if p.rsplit("/", 1)[0] != dst: plan.append((ad.get_asset(), dst, name))
cnt = collections.Counter(d for _, d, _ in plan)
for d, n in sorted(cnt.items()): log("%-28s %d" % (d, n))
misc = [n for _, d, n in plan if d.endswith("Misc")]
log("Misc: " + ", ".join(sorted(misc)))
if GO:
    at = unreal.AssetToolsHelpers.get_asset_tools()
    data = [unreal.AssetRenameData(asset=a, new_package_path=d, new_name=n) for a, d, n in plan]
    ok = at.rename_assets(data)
    log("rename_assets ok=%s (%d)" % (ok, len(data)))
    # remove redirectors left in the old folders
    reds = []
    for folder in (R + "/Scene", R + "/Sim"):
        for ad in ar.get_assets_by_path(folder, True):
            if str(ad.asset_class_path.asset_name) == "ObjectRedirector": reds.append(ad.get_asset())
    if reds:
        at.fixup_referencers(reds)
    log("redirectors fixed: %d" % len(reds))
    unreal.EditorAssetLibrary.save_directory(R, only_if_is_dirty=True, recursive=True)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    log("saved")
