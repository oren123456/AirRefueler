"""Import the baked Mirage-style cockpit atlas (Tools/cockpit_bake.py -> Data/Generated) and use it on both cockpit
material instances (BaseColorTex + NormalTex). argv 'orig' switches back to the original atlas."""
import unreal, os, sys
eal = unreal.EditorAssetLibrary; mel = unreal.MaterialEditingLibrary; at = unreal.AssetToolsHelpers.get_asset_tools()
TEX = "/Game/AirRefueler/Textures"; MAT = "/Game/AirRefueler/Materials"
root = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
log = lambda s: unreal.log("[CockpitTex] " + s)
if len(sys.argv) > 1 and sys.argv[1] == "orig":
    base, nrm = eal.load_asset(TEX + "/T_Salon_Diffuse"), None
else:
    for n in ("T_Salon_Diffuse_Mirage", "T_Salon_Normal_Mirage"):
        t = unreal.AssetImportTask(); t.filename = os.path.join(root, "Data", "Generated", n + ".png")
        t.destination_path = TEX; t.destination_name = n; t.automated = True; t.replace_existing = True; t.save = True
        at.import_asset_tasks([t])
    base = eal.load_asset(TEX + "/T_Salon_Diffuse_Mirage"); nrm = eal.load_asset(TEX + "/T_Salon_Normal_Mirage")
    nrm.set_editor_property("srgb", False); nrm.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
    eal.save_loaded_asset(nrm)
for mi_name in ("MI_Salon_VRay1", "MI_Salon_VRay1_Cutout"):
    mi = eal.load_asset(MAT + "/" + mi_name)
    mel.set_material_instance_texture_parameter_value(mi, "BaseColorTex", base)
    if nrm: mel.set_material_instance_texture_parameter_value(mi, "NormalTex", nrm)
    mel.update_material_instance(mi); eal.save_loaded_asset(mi)
    log("%s -> %s" % (mi_name, base.get_name()))
log("done")
