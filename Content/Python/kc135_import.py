"""KC-135 import (Data/KC-135 Stratotanker): textures -> /Game/AirRefueler/KC135/Textures, 8 OBJ parts -> .../Meshes.
OBJ = metres, Y-up, nose +Z, no .mtl. Logs mesh bounds to Saved/ClaudeShots/kc135_import.json."""
import unreal, os, json
at = unreal.AssetToolsHelpers.get_asset_tools(); eal = unreal.EditorAssetLibrary
src = r"D:/GitHub/AirRefueler/Data/KC-135 Stratotanker"
D = "/Game/AirRefueler/KC135"
out = {"tex": [], "mesh": {}}
tasks = []
for f in sorted(os.listdir(src)):
    if f.lower().endswith(".png"):
        n = "T_KC135_" + os.path.splitext(f)[0]
        t = unreal.AssetImportTask(); t.filename = os.path.join(src, f); t.destination_path = D + "/Textures"; t.destination_name = n
        t.automated = True; t.replace_existing = True; t.save = False; tasks.append(t)
at.import_asset_tasks(tasks)
for t in tasks:
    n = t.destination_name; a = eal.load_asset(D + "/Textures/" + n)
    if a is None: out["tex"].append([n, "FAIL"]); continue
    low = n.lower()
    if low.endswith("_normal"):
        a.set_editor_property("srgb", False); a.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
    elif low.endswith(("_ao", "_metallic", "_roughness", "_opacity")):
        a.set_editor_property("srgb", False); a.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
    eal.save_loaded_asset(a); out["tex"].append([n, a.blueprint_get_size_x()])
for i in range(8):
    t = unreal.AssetImportTask(); t.filename = os.path.join(src, "model_%d.obj" % i); t.destination_path = D + "/Meshes"; t.destination_name = "SM_KC135_%d" % i
    t.automated = True; t.replace_existing = True; t.save = True
    at.import_asset_tasks([t])
    objs = [str(p) for p in t.imported_object_paths]
    m = None
    for p in objs:
        a = unreal.load_asset(p)
        if isinstance(a, unreal.StaticMesh): m = a
    if m is None: out["mesh"][i] = {"imported": objs}; continue
    b = m.get_bounding_box()
    out["mesh"][i] = {"path": m.get_path_name(), "min": [round(b.min.x), round(b.min.y), round(b.min.z)], "max": [round(b.max.x), round(b.max.y), round(b.max.z)], "mats": m.get_num_sections(0), "other": [p for p in objs if p != m.get_path_name()]}
open(r"D:/GitHub/AirRefueler/Saved/ClaudeShots/kc135_import.json", "w").write(json.dumps(out, indent=1))
unreal.log("[KC135] import done")
