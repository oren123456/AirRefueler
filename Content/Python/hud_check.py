import unreal
mel = unreal.MaterialEditingLibrary
m = unreal.EditorAssetLibrary.load_asset("/Game/AirRefueler/Sim/HUD/M_HUD")
out = ["Brightness %s" % mel.get_material_default_scalar_parameter_value(m, "Brightness"),
       "HudColor %s" % mel.get_material_default_vector_parameter_value(m, "HudColor"),
       "GlassOpacity %s" % mel.get_material_default_scalar_parameter_value(m, "GlassOpacity")]
for e in mel.get_used_textures(m): out.append("tex %s" % e.get_name())
open(unreal.Paths.project_saved_dir() + "ClaudeShots/hud_check.txt", "w").write("\n".join(out))
