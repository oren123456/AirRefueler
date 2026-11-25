import unreal
m = unreal.EditorAssetLibrary.load_asset("/Game/AirRefueler/Sim/Meshes/SM_GroundCap")
ns = m.get_editor_property("nanite_settings")
out = ["nanite enabled=%s" % ns.get_editor_property("enabled")]
out.append("lods=%d tris=%d" % (m.get_num_lods(), unreal.EditorStaticMeshLibrary.get_number_verts(m, 0)))
open(unreal.Paths.project_saved_dir() + "ClaudeShots/ground_check.txt", "w").write("\n".join(out))
