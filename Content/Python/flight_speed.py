"""One flight speed (m/s, relative to the air/ground) for every motion cue: volumetric cloud deck wind,
ground scroll (MPC_Flight.Speed, read by M_Ground and M_CloudPuff), cloud puffs (BP_CloudStream.Speed).
argv: speed m/s (default 250). Creates MPC_Flight if missing."""
import unreal, sys
v = float(sys.argv[1]) if len(sys.argv) > 1 else 250.0
eal = unreal.EditorAssetLibrary; mel = unreal.MaterialEditingLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
P = "/Game/AirRefueler/Sim/MPC_Flight"
if not eal.does_asset_exist(P):
    unreal.AssetToolsHelpers.get_asset_tools().create_asset("MPC_Flight", "/Game/AirRefueler/Sim", unreal.MaterialParameterCollection, unreal.MaterialParameterCollectionFactoryNew())
mpc = eal.load_asset(P)
cur = list(mpc.get_editor_property("scalar_parameters"))
sp = [x for x in cur if str(x.get_editor_property("parameter_name")) == "Speed"]
if sp: sp[0].set_editor_property("default_value", v)
else:
    x = unreal.CollectionScalarParameter(); x.set_editor_property("parameter_name", "Speed"); x.set_editor_property("default_value", v); cur.append(x)
mpc.set_editor_property("scalar_parameters", cur); eal.save_loaded_asset(mpc)
mi = unreal.load_asset("/Game/AirRefueler/Maps/MI_VolumetricCloud_Refuel")
mel.set_material_instance_vector_parameter_value(mi, "Layout_WindControls", unreal.LinearColor(0.0, v / 375.0, 0.04, 1.0))   # wind 1.0 ~= 375 m/s
mel.update_material_instance(mi); eal.save_loaded_asset(mi)
bp = "/Game/AirRefueler/Sim/Clouds/BP_CloudStream"
if eal.does_asset_exist(bp):
    unreal.BlueprintEditorLibrary.compile_blueprint(eal.load_asset(bp))
    cdo = unreal.get_default_object(eal.load_asset(bp).generated_class()); cdo.set_editor_property("Speed", v * 100.0)
    if cdo.get_editor_property("ThroughChance") == 0.0: cdo.set_editor_property("ThroughChance", 0.15)   # ~1 in 7 puffs on the formation's track
    for a in eas.get_all_level_actors():
        if a.get_class().get_name().startswith("BP_CloudStream"):
            a.set_editor_property("Speed", v * 100.0); a.set_editor_property("ThroughChance", cdo.get_editor_property("ThroughChance"))
    eal.save_loaded_asset(eal.load_asset(bp))
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
unreal.log("[FlightSpeed] %.0f m/s" % v)
