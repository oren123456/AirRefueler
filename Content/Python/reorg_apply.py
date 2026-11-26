"""Per-model material/texture folders + delete unused materials (plan from reorg_plan.py).
Models/Aircraft/{B767,Mirage}/{Materials,Textures}, Models/Drogue/{Materials,Textures}; shared masters stay in
/Game/AirRefueler/Materials. Writes old->new path map to Saved/ClaudeShots/reorg_map.json."""
import unreal, json
R = "/Game/AirRefueler"
eal = unreal.EditorAssetLibrary; at = unreal.AssetToolsHelpers.get_asset_tools()
plan = json.load(open(r"D:/GitHub/AirRefueler/Saved/ClaudeShots/reorg_plan.json"))
log = {"deleted": [], "delete_failed": [], "moved": {}, "move_failed": []}
eal.save_directory(R, only_if_is_dirty=True, recursive=True)
# 1) delete unused materials (instances first, then parents)
dm = sorted(plan["delete_mat"], key=lambda p: 0 if unreal.EditorAssetLibrary.find_asset_data(p).asset_class_path.asset_name == "MaterialInstanceConstant" else 1)
for p in dm:
    try:
        ok = eal.delete_asset(p)
    except Exception as e:
        ok = False
    (log["deleted"] if ok else log["delete_failed"]).append(p)
# 2) moves
DEST = {"B767": R + "/Models/Aircraft/B767", "Mirage": R + "/Models/Aircraft/Mirage", "Drogue": R + "/Models/Drogue"}
KEEP_SHARED = {R + "/Materials/M_MayaPBR", R + "/Materials/M_MayaGlass"}
moves = {}
for p, users in plan["mat"].items():
    if p in KEEP_SHARED or "/KC135/" in p: continue
    if p.endswith("MI_Salon_VRay1_Cutout"): users = ["Mirage"]
    if len(users) == 1 and users[0] in DEST:
        moves[p] = DEST[users[0]] + "/Materials/" + p.split("/")[-1]
for p, users in plan["tex"].items():
    if "/KC135/" in p or p.endswith("T_HUDFont"): continue
    if p.endswith("T_Mirage_Devices_HUD_Mask"): users = ["Mirage"]
    if len(users) == 1 and users[0] in DEST:
        moves[p] = DEST[users[0]] + "/Textures/" + p.split("/")[-1]
for d in set(v.rsplit("/", 1)[0] for v in moves.values()): eal.make_directory(d)
data = []
for src, dst in moves.items():
    a = eal.load_asset(src)
    if a is None: log["move_failed"].append(src); continue
    data.append(unreal.AssetRenameData(a, dst.rsplit("/", 1)[0], dst.rsplit("/", 1)[1]))
ok = at.rename_assets(data)
for src, dst in moves.items():
    if eal.does_asset_exist(dst): log["moved"][src] = dst
    else: log["move_failed"].append(src)
# 3) fix up redirectors left in the old folders
ar = unreal.AssetRegistryHelpers.get_asset_registry()
reds = []
for f in (R + "/Materials", R + "/Textures", R + "/Scene", R + "/Sim/Materials"):
    for ad in ar.get_assets_by_path(f, recursive=True):
        if str(ad.asset_class_path.asset_name) == "ObjectRedirector":
            o = eal.load_asset(str(ad.package_name))
            if o: reds.append(o)
if reds: at.fixup_referencers(reds)
log["redirectors_fixed"] = len(reds)
eal.save_directory(R, only_if_is_dirty=True, recursive=True)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
open(r"D:/GitHub/AirRefueler/Saved/ClaudeShots/reorg_map.json", "w").write(json.dumps(log, indent=0))
open(r"D:/GitHub/AirRefueler/Saved/ClaudeShots/reorg_res.json", "w").write(json.dumps({"deleted": len(log["deleted"]), "delete_failed": log["delete_failed"], "moved": len(log["moved"]), "move_failed": log["move_failed"], "rename_ok": ok, "redirectors": len(reds)}))
