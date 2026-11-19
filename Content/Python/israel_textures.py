"""Swap the base-color textures that carried Indian markings for the Israeli versions
in Data/Generated/*_IL.png (made by Tools/israel_markings.py). Re-runnable; originals untouched."""
import os, unreal
GEN = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()), "Data", "Generated")
TEX, MAT = "/Game/AirRefueler/Textures", "/Game/AirRefueler/Materials"
eal = unreal.EditorAssetLibrary; mel = unreal.MaterialEditingLibrary
at = unreal.AssetToolsHelpers.get_asset_tools()
log = lambda *x: unreal.log("[IsraelTex] " + " ".join(str(v) for v in x))
STEMS = ["Su-30_Body_Diffuse_Edited", "body_DFM_Edited", "Top_Mian_Wing_Fliped_DFM",
         "wing_Bottom_DFM_Edited", "wing_top_DFM_Edited", "Housing_Diffuse_Edited"]
norm = lambda s: s.replace("-", "_").replace(" ", "_").lower()

new = {}
for st in STEMS:
    name = "T_" + st.replace("-", "_") + "_IL"
    t = unreal.AssetImportTask(); t.filename = os.path.join(GEN, st + "_IL.png"); t.destination_path = TEX
    t.destination_name = name; t.automated = True; t.replace_existing = True; t.save = True
    at.import_asset_tasks([t])
    new[norm(st)] = eal.load_asset(TEX + "/" + name)

changed = 0
for p in eal.list_assets(MAT, recursive=True, include_folder=False):
    mi = eal.load_asset(p)
    if not isinstance(mi, unreal.MaterialInstanceConstant):
        continue
    cur = mel.get_material_instance_texture_parameter_value(mi, "BaseColorTex")
    if not cur:
        continue
    key = norm(cur.get_name()).removeprefix("t_").removesuffix("_il")
    tgt = new.get(key)
    if tgt is None or cur == tgt:
        if tgt is not None: log("already", mi.get_name())
        continue
    old = cur.get_name()
    # keep the original texture's settings (sRGB, compression, max size)
    for prop in ("srgb", "compression_settings", "max_texture_size", "lod_group"):
        try: tgt.set_editor_property(prop, cur.get_editor_property(prop))
        except Exception: pass
    eal.save_loaded_asset(tgt)
    mel.set_material_instance_texture_parameter_value(mi, "BaseColorTex", tgt)
    mel.update_material_instance(mi); eal.save_loaded_asset(mi); changed += 1
    log(mi.get_name(), old, "->", tgt.get_name())
log("done, MIs changed:", changed)
