import unreal, json
eal = unreal.EditorAssetLibrary; mel = unreal.MaterialEditingLibrary
res = []
mis = set()
for p in eal.list_assets("/Game/AirRefueler/Materials", recursive=True, include_folder=False):
    mi = eal.load_asset(p)
    if isinstance(mi, unreal.MaterialInstanceConstant):
        t = mel.get_material_instance_texture_parameter_value(mi, "BaseColorTex")
        if t and "droug" in t.get_name().lower(): mis.add(mi.get_path_name())
for p in eal.list_assets("/Game/AirRefueler/Scene", recursive=True, include_folder=False):
    a = eal.find_asset_data(p)
    if str(a.asset_class_path.asset_name) != "StaticMesh": continue
    sm = eal.load_asset(p)
    ms = [m.material_interface.get_path_name() for m in sm.static_materials if m.material_interface]
    if any(m in mis for m in ms):
        b = sm.get_bounding_box()
        res.append([p, ms, [b.min.x, b.min.y, b.min.z, b.max.x, b.max.y, b.max.z], sm.get_num_triangles(0)])
json.dump({"mis": sorted(mis), "meshes": res}, open(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()) + "ClaudeShots/drogue.json", "w"), indent=1)
unreal.log("[Drogue] %d meshes" % len(res))
