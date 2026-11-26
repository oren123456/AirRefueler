"""KC-135 materials + BP_KC135 (8 parts, built at x100, roll 90: OBJ Y-up/nose +Z -> UE Z-up/nose +Y) + preview actor.
argv: optional 'map' JSON override, e.g. {"0":"cockpit"}. Re-runnable."""
import unreal, json, sys
eal = unreal.EditorAssetLibrary; mel = unreal.MaterialEditingLibrary; at = unreal.AssetToolsHelpers.get_asset_tools()
D = "/Game/AirRefueler/Models/Aircraft/KC135"; TX = D + "/Textures/T_KC135_"
log = lambda s: unreal.log("[KC135] " + s)
MAP = {"0": "cockpit", "1": "fuz", "2": "wings", "3": "wings", "4": "int", "5": "Dashboard", "6": "Detail", "7": "glass"}
if len(sys.argv) > 1: MAP.update(json.loads(sys.argv[1]))
def master(name, glass):
    p = D + "/Materials/" + name
    if eal.does_asset_exist(p): return eal.load_asset(p)
    m = at.create_asset(name, D + "/Materials", unreal.Material, unreal.MaterialFactoryNew())
    E = lambda c, x, y: mel.create_material_expression(m, c, x, y)
    def tp(pn, x, y, st):
        e = E(unreal.MaterialExpressionTextureSampleParameter2D, x, y); e.set_editor_property("parameter_name", pn); e.set_editor_property("sampler_type", st); return e
    col = tp("Albedo", -800, -300, unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
    col.set_editor_property("texture", eal.load_asset(TX + "fuz_albedo"))
    nrm = tp("Normal", -800, 0, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL); nrm.set_editor_property("texture", eal.load_asset(TX + "fuz_normal"))
    rgh = tp("Roughness", -800, 300, unreal.MaterialSamplerType.SAMPLERTYPE_MASKS); rgh.set_editor_property("texture", eal.load_asset(TX + "fuz_roughness"))
    mel.connect_material_property(col, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(nrm, "RGB", unreal.MaterialProperty.MP_NORMAL)
    mel.connect_material_property(rgh, "R", unreal.MaterialProperty.MP_ROUGHNESS)
    if glass:
        m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
        m.set_editor_property("translucency_lighting_mode", unreal.TranslucencyLightingMode.TLM_SURFACE_FORWARD_SHADING) if hasattr(unreal.TranslucencyLightingMode, "TLM_SURFACE_FORWARD_SHADING") else None
        op = tp("Opacity", -800, 600, unreal.MaterialSamplerType.SAMPLERTYPE_MASKS); op.set_editor_property("texture", eal.load_asset(TX + "glass_opacity"))
        mel.connect_material_property(op, "R", unreal.MaterialProperty.MP_OPACITY)
        sp = E(unreal.MaterialExpressionConstant, -400, 700); sp.set_editor_property("r", 1.0)
        mel.connect_material_property(sp, "", unreal.MaterialProperty.MP_SPECULAR)
    else:
        met = tp("Metallic", -800, 600, unreal.MaterialSamplerType.SAMPLERTYPE_MASKS); met.set_editor_property("texture", eal.load_asset(TX + "fuz_metallic"))
        ao = tp("AO", -800, 900, unreal.MaterialSamplerType.SAMPLERTYPE_MASKS); ao.set_editor_property("texture", eal.load_asset(TX + "fuz_AO"))
        mel.connect_material_property(met, "R", unreal.MaterialProperty.MP_METALLIC)
        mel.connect_material_property(ao, "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    m.set_editor_property("two_sided", glass)
    mel.recompile_material(m); eal.save_loaded_asset(m); return m
M = master("M_KC135", False); MG = master("M_KC135_Glass", True)
def mi(set_):
    p = D + "/Materials/MI_KC135_" + set_
    m = eal.load_asset(p) if eal.does_asset_exist(p) else at.create_asset("MI_KC135_" + set_, D + "/Materials", unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    glass = set_ == "glass"
    m.set_editor_property("parent", MG if glass else M)
    chans = [("Albedo", "albedo"), ("Normal", "normal"), ("Roughness", "roughness")] + ([("Opacity", "opacity")] if glass else [("Metallic", "metallic"), ("AO", "AO")])
    for pn, suf in chans:
        t = eal.load_asset(TX + set_ + "_" + suf)
        if t: mel.set_material_instance_texture_parameter_value(m, pn, t)
    mel.update_material_instance(m); eal.save_loaded_asset(m); return m
mis = {s: mi(s) for s in set(MAP.values())}
for i, s in MAP.items():
    sm = eal.load_asset(D + "/Meshes/SM_KC135_" + i)
    sm.set_material(0, mis[s])
    ns = sm.get_editor_property("nanite_settings")
    if ns.enabled:   # ~200k tris total: plain meshes (Nanite showed its coarse fallback on the wheels)
        ns.enabled = False; sm.set_editor_property("nanite_settings", ns)
    # OBJ came in at 1 m -> 1 cm: build at x100 so small triangles are not merged as degenerate (faceted wheels)
    smes = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    bs = smes.get_lod_build_settings(sm, 0)
    if bs.build_scale3d.x != 100.0 or bs.remove_degenerates:
        bs.build_scale3d = unreal.Vector(100.0, 100.0, 100.0); bs.remove_degenerates = False
        smes.set_lod_build_settings(sm, 0, bs)
    eal.save_loaded_asset(sm)
# blueprint
bp_path = D + "/BP_KC135"
if not eal.does_asset_exist(bp_path):
    f = unreal.BlueprintFactory(); f.set_editor_property("parent_class", unreal.Actor)
    at.create_asset("BP_KC135", D, unreal.Blueprint, f)
bp = eal.load_asset(bp_path)
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem); L = unreal.SubobjectDataBlueprintFunctionLibrary
handles = sds.k2_gather_subobject_data_for_blueprint(bp)
have = {str(L.get_variable_name(L.get_data(h))): h for h in handles}
# model_3 = the left main-gear wheels missing from model_2 (mirror of the right set, <2 cm): uses the wings/gear set
SKIP = set()
for i in range(8):
    if i in SKIP: continue
    n = "Part%d" % i
    if n in have: h = have[n]
    else:
        h, why = sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=handles[0], new_class=unreal.StaticMeshComponent, blueprint_context=bp))
        sds.rename_subobject(h, unreal.Text(n))
    c = L.get_object(L.get_data(h))
    c.set_editor_property("static_mesh", eal.load_asset(D + "/Meshes/SM_KC135_%d" % i))
    c.set_editor_property("relative_rotation", unreal.Rotator(roll=90.0, pitch=0.0, yaw=0.0))
    c.set_editor_property("relative_scale3d", unreal.Vector(1.0, 1.0, 1.0))
unreal.BlueprintEditorLibrary.compile_blueprint(bp); eal.save_loaded_asset(bp)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in eas.get_all_level_actors():
    if a.get_actor_label() == "KC135_Preview": eas.destroy_actor(a)
a = eas.spawn_actor_from_class(bp.generated_class(), unreal.Vector(7000.0, 0.0, 0.0)); a.set_actor_label("KC135_Preview")
o, e = a.get_actor_bounds(False)
res = {"ctr": [round(o.x), round(o.y), round(o.z)], "ext": [round(e.x), round(e.y), round(e.z)], "map": MAP}
for c in a.get_components_by_class(unreal.StaticMeshComponent):
    oo, ee, rr = unreal.SystemLibrary.get_component_bounds(c)
    res[c.get_name()] = [round(oo.x), round(oo.y), round(oo.z), round(ee.x), round(ee.y), round(ee.z)]
open(r"D:/GitHub/AirRefueler/Saved/ClaudeShots/kc135_bp.json", "w").write(json.dumps(res, indent=1))
log("bp done")
