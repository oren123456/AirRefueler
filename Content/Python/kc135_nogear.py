"""KC-135 without landing gear: reimport SM_KC135_1/2/6 from Data/Generated/KC135 (gear deleted + wheel wells capped
in Blender), drop Part3 (left main wheels) from BP_KC135 and delete SM_KC135_3. Re-runnable."""
import unreal, os, json
at = unreal.AssetToolsHelpers.get_asset_tools(); eal = unreal.EditorAssetLibrary
src = r"D:/GitHub/AirRefueler/Data/Generated/KC135"
D = "/Game/AirRefueler/Models/Aircraft/KC135"
MAP = {"1": "fuz", "2": "wings", "6": "Detail"}
smes = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
out = {}
for i, s in MAP.items():
    t = unreal.AssetImportTask(); t.filename = os.path.join(src, "model_%s.obj" % i); t.destination_path = D + "/Meshes"
    t.destination_name = "SM_KC135_" + i; t.automated = True; t.replace_existing = True; t.save = False
    at.import_asset_tasks([t])
    extra = [str(p) for p in t.imported_object_paths if not str(p).startswith(D + "/Meshes/SM_KC135_" + i)]
    for p in extra:   # interchange may create a default material; not wanted
        if eal.does_asset_exist(p.split(".")[0]) and not eal.find_package_referencers_for_asset(p.split(".")[0]): eal.delete_asset(p.split(".")[0])
    sm = eal.load_asset(D + "/Meshes/SM_KC135_" + i)
    sm.set_material(0, eal.load_asset(D + "/Materials/MI_KC135_" + s))
    ns = sm.get_editor_property("nanite_settings")
    if ns.enabled: ns.enabled = False; sm.set_editor_property("nanite_settings", ns)
    bs = smes.get_lod_build_settings(sm, 0)
    bs.build_scale3d = unreal.Vector(100.0, 100.0, 100.0); bs.remove_degenerates = False
    smes.set_lod_build_settings(sm, 0, bs)
    eal.save_loaded_asset(sm)
    b = sm.get_bounding_box()
    out[i] = {"tris": smes.get_number_verts(sm, 0), "min": [round(b.min.x), round(b.min.y), round(b.min.z)], "max": [round(b.max.x), round(b.max.y), round(b.max.z)], "extra": extra}
# remove Part3 from the blueprint
bp = eal.load_asset(D + "/BP_KC135")
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem); L = unreal.SubobjectDataBlueprintFunctionLibrary
handles = sds.k2_gather_subobject_data_for_blueprint(bp)
for h in handles:
    if str(L.get_variable_name(L.get_data(h))) == "Part3":
        out["del_part3"] = sds.delete_subobjects(handles[0], [h], bp)
unreal.BlueprintEditorLibrary.compile_blueprint(bp); eal.save_loaded_asset(bp)
p3 = D + "/Meshes/SM_KC135_3"
if eal.does_asset_exist(p3):
    refs = [str(r) for r in eal.find_package_referencers_for_asset(p3)]
    out["sm3_refs"] = refs
    if not refs: out["sm3_deleted"] = eal.delete_asset(p3)
out["parts"] = [str(L.get_variable_name(L.get_data(h))) for h in sds.k2_gather_subobject_data_for_blueprint(bp)]
open(r"D:/GitHub/AirRefueler/Saved/ClaudeShots/kc135_nogear.json", "w").write(json.dumps(out, indent=1))
unreal.log("[KC135] nogear done")
