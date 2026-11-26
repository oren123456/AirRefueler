"""Hose look: black hose with light bands ~every metre (M_HoseStripes, procedural from the cable UV along its length,
TileMaterial = number of bands), full gravity + more segments so the slack hangs in a smooth bow. Re-runnable."""
import unreal
SIM = "/Game/AirRefueler/Sim"; MATDIR = "/Game/AirRefueler/Models/Drogue/Materials"
eal = unreal.EditorAssetLibrary; at = unreal.AssetToolsHelpers.get_asset_tools(); mel = unreal.MaterialEditingLibrary
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem); SDL = unreal.SubobjectDataBlueprintFunctionLibrary
log = lambda s: unreal.log("[HoseLook] " + s)
mp = MATDIR + "/M_HoseStripes"
if eal.does_asset_exist(mp): eal.delete_asset(mp)
m = at.create_asset("M_HoseStripes", MATDIR, unreal.Material, unreal.MaterialFactoryNew())
E = lambda cls, x, y: mel.create_material_expression(m, cls, x, y)
uv = E(unreal.MaterialExpressionTextureCoordinate, -1100, 0)
mask = E(unreal.MaterialExpressionComponentMask, -900, 0)
mask.set_editor_property("r", True); mask.set_editor_property("g", False); mask.set_editor_property("b", False); mask.set_editor_property("a", False)
fr = E(unreal.MaterialExpressionFrac, -750, 0)
w = E(unreal.MaterialExpressionScalarParameter, -750, 150); w.set_editor_property("parameter_name", "BandWidth"); w.set_editor_property("default_value", 0.14)
sub = E(unreal.MaterialExpressionSubtract, -600, 50)
mul = E(unreal.MaterialExpressionMultiply, -450, 50); mul.set_editor_property("const_b", 60.0)
sat = E(unreal.MaterialExpressionSaturate, -300, 50)
dark = E(unreal.MaterialExpressionVectorParameter, -450, -200); dark.set_editor_property("parameter_name", "HoseColor"); dark.set_editor_property("default_value", unreal.LinearColor(0.018, 0.018, 0.018, 1))
band = E(unreal.MaterialExpressionVectorParameter, -450, -350); band.set_editor_property("parameter_name", "BandColor"); band.set_editor_property("default_value", unreal.LinearColor(0.45, 0.40, 0.30, 1))
lerp = E(unreal.MaterialExpressionLinearInterpolate, -150, -100)
rough = E(unreal.MaterialExpressionConstant, -150, 150); rough.set_editor_property("r", 0.55)
mel.connect_material_expressions(uv, "", mask, "")
mel.connect_material_expressions(mask, "", fr, "")
mel.connect_material_expressions(w, "", sub, "A"); mel.connect_material_expressions(fr, "", sub, "B")
mel.connect_material_expressions(sub, "", mul, "A")
mel.connect_material_expressions(mul, "", sat, "")
mel.connect_material_expressions(dark, "", lerp, "A"); mel.connect_material_expressions(band, "", lerp, "B"); mel.connect_material_expressions(sat, "", lerp, "Alpha")
mel.connect_material_property(lerp, "", unreal.MaterialProperty.MP_BASE_COLOR)
mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
mel.recompile_material(m); eal.save_loaded_asset(m)
bp = eal.load_asset(SIM + "/BP_RefuelHose")
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    o = SDL.get_object(SDL.get_data(h))
    if o and o.get_name().startswith("Hose") and isinstance(o, unreal.CableComponent):
        log("before: segments=%s tile=%s width=%s grav=%s mat=%s" % (o.get_editor_property("num_segments"), o.get_editor_property("tile_material"), o.get_editor_property("cable_width"), o.get_editor_property("cable_gravity_scale"), o.get_material(0)))
        o.set_material(0, m)
        o.set_editor_property("tile_material", 24.0)
        o.set_editor_property("num_segments", 24)
        o.set_editor_property("cable_gravity_scale", 1.0)
        o.set_editor_property("solver_iterations", 16)
        log("after: segments=24 tile=24 grav=1.0 mat=M_HoseStripes")
unreal.BlueprintEditorLibrary.compile_blueprint(bp); eal.save_loaded_asset(bp)
log("done")
# level instance had its own material override (MI_phong1) -> use the striped material there too
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in eas.get_all_level_actors():
    if a.get_class() == bp.generated_class():
        c = a.get_component_by_class(unreal.CableComponent)
        c.modify(); c.set_material(0, m)
        log("instance %s mat=%s" % (a.get_actor_label(), c.get_material(0).get_name()))
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
