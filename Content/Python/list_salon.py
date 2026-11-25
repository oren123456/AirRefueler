import unreal
eal = unreal.EditorAssetLibrary
out = []
out.append("n textures dir: %d" % len(eal.list_assets("/Game/AirRefueler/Textures", recursive=True, include_folder=False)))
mi = eal.load_asset("/Game/AirRefueler/Materials/MI_Salon_VRay1")
out.append("mi %s class %s" % (mi, mi.get_class().get_name() if mi else None))
if mi:
    for n in ["parent", "texture_parameter_values", "scalar_parameter_values", "vector_parameter_values"]:
        try: out.append("%s = %s" % (n, mi.get_editor_property(n)))
        except Exception as e: out.append("%s ERR %s" % (n, e))
    try:
        for t in unreal.MaterialEditingLibrary.get_used_textures(mi): out.append("used tex %s %dx%d" % (t.get_path_name(), t.blueprint_get_size_x(), t.blueprint_get_size_y()))
    except Exception as e: out.append("used ERR %s" % e)
open(unreal.Paths.project_saved_dir() + "ClaudeShots/list_salon.txt", "w").write("\n".join(str(x) for x in out))
