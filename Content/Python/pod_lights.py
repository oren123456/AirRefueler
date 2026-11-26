"""Pod signal lights on BP_RefuelHose: red / amber / green emissive lamps on the lower aft pod, next to the hose exit
(actor origin = pod tail). Unlit emissive material M_PodLight (Color, Intensity) + 3 MIs. Re-runnable.
Logic (BP graph): trailing/rewinding = red, READY or connected without flow = amber, fuel flowing = green, stowed = off."""
import unreal
SIM = "/Game/AirRefueler/Sim"; MATDIR = "/Game/AirRefueler/Models/Drogue/Materials"
eal = unreal.EditorAssetLibrary; at = unreal.AssetToolsHelpers.get_asset_tools(); mel = unreal.MaterialEditingLibrary
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem); SDL = unreal.SubobjectDataBlueprintFunctionLibrary
log = lambda s: unreal.log("[PodLights] " + s)
# ---- material
mp = MATDIR + "/M_PodLight"
if not eal.does_asset_exist(mp):
    m = at.create_asset("M_PodLight", MATDIR, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    col = mel.create_material_expression(m, unreal.MaterialExpressionVectorParameter, -500, 0)
    col.set_editor_property("parameter_name", "Color"); col.set_editor_property("default_value", unreal.LinearColor(1, 0, 0, 1))
    inten = mel.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -500, 200)
    inten.set_editor_property("parameter_name", "Intensity"); inten.set_editor_property("default_value", 40.0)
    mul = mel.create_material_expression(m, unreal.MaterialExpressionMultiply, -250, 100)
    mel.connect_material_expressions(col, "", mul, "A"); mel.connect_material_expressions(inten, "", mul, "B")
    mel.connect_material_property(mul, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(m); eal.save_loaded_asset(m)
m = eal.load_asset(mp)
COLS = {"Red": unreal.LinearColor(1.0, 0.02, 0.01, 1), "Amber": unreal.LinearColor(1.0, 0.45, 0.0, 1), "Green": unreal.LinearColor(0.05, 1.0, 0.1, 1)}
mis = {}
for n, c in COLS.items():
    p = MATDIR + "/MI_PodLight_" + n
    mi = eal.load_asset(p) if eal.does_asset_exist(p) else at.create_asset("MI_PodLight_" + n, MATDIR, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mi.set_editor_property("parent", m)
    mel.set_material_instance_vector_parameter_value(mi, "Color", c)
    mel.set_material_instance_scalar_parameter_value(mi, "Intensity", 300.0)
    mel.update_material_instance(mi); eal.save_loaded_asset(mi); mis[n] = mi
# ---- components
bp = eal.load_asset(SIM + "/BP_RefuelHose")
def comps():
    out = {}
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        o = SDL.get_object(SDL.get_data(h))
        if o: out[o.get_name().replace("_GEN_VARIABLE", "")] = (h, o)
    return out
c = comps()
root = next(k for k, (h, o) in c.items() if isinstance(o, unreal.SceneComponent) and o.get_attach_parent() is None and k not in ("Parachute", "Body", "Hose"))
sphere = eal.load_asset("/Engine/BasicShapes/Sphere")
# pod tail = actor origin; pod radius ~38 cm. Row of lamps on the lower aft pod, +X = left of the tanker.
POS = {"Red": unreal.Vector(27.0, 30.0, -32.0), "Amber": unreal.Vector(0.0, 30.0, -38.0), "Green": unreal.Vector(-27.0, 30.0, -32.0)}
for n in COLS:
    name = "Light" + n
    if name not in c:
        h, fail = sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=c[root][0], new_class=unreal.StaticMeshComponent, blueprint_context=bp))
        sds.rename_subobject(h, unreal.Text(name)); c = comps()
    o = c[name][1]
    o.set_editor_property("static_mesh", sphere)
    o.set_material(0, mis[n])
    o.set_editor_property("relative_location", POS[n])
    o.set_editor_property("relative_scale3d", unreal.Vector(0.22, 0.22, 0.22))
    o.set_collision_profile_name("NoCollision")
    o.set_editor_property("cast_shadow", False)
    o.set_editor_property("visible", n == "Amber")
    log("%s at %s (root %s)" % (name, POS[n], root))
unreal.BlueprintEditorLibrary.compile_blueprint(bp); eal.save_loaded_asset(bp)
log("done")
