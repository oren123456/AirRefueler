import unreal
mel = unreal.MaterialEditingLibrary
mi = unreal.load_asset("/Game/AirRefueler/Maps/MI_VolumetricCloud_Refuel")
for n in ("Layout_WindControls", "Layout_GlobalTexturePlacement", "Noise1_Coordinates", "Noise2_Coordinates", "Noise3_Coordinates"):
    unreal.log("[CloudWind] %s = %s" % (n, mel.get_material_instance_vector_parameter_value(mi, n)))
par = mi.get_base_material()
unreal.log("[CloudWind] base %s" % par.get_path_name())
# find the expressions that read the wind param and what they feed
exprs = unreal.MaterialEditingLibrary.get_num_material_expressions(par)
unreal.log("[CloudWind] expr count %d" % exprs)
