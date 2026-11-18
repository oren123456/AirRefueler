"""Cockpit glass: translucent material driven by the VRay refraction masks.
Su-30 / Mirage canopies share the hull texture atlas; the white areas of the *_Refraction.png
masks are glass. 767 glass1 is clear glass (VRayMtl15). Assigns on the mesh assets used by
the canopy actors only. Re-runnable."""
import os, unreal

ROOT = "/Game/AirRefueler"
TEX = ROOT + "/Textures"
MAT = ROOT + "/Materials"
DATA = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()), "Data")
at = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
log = lambda *a: unreal.log("[Glass] " + " ".join(str(x) for x in a))

# canopy actor label -> (glass MI name, base texture, refraction mask)
CANOPIES = {
    "WindShield":    "MI_Glass_Su30",
    "Cockpit_Glass": "MI_Glass_Mirage",
    "Dome_Glass":    "MI_Glass_Mirage",
    "Dome_Glass2":   "MI_Glass_Mirage",
    "glass1":        "MI_Glass_767",
    "Signal_Lights": "MI_Glass_Mirage",   # light lenses are in the refraction mask too
}
GLASS_MI = {
    "MI_Glass_Su30":   dict(base="T_Su_30_Body_Diffuse_Edited", refr="Su-30_Body_Refraction"),
    "MI_Glass_Mirage": dict(base="T_Housing_Diffuse_Edited", refr="Housing_Refraction"),
    "MI_Glass_767":    dict(base=None, refr=None),            # whole mesh is glass
}


def find_file(stem):
    for r, _, fs in os.walk(DATA):
        for f in fs:
            if os.path.splitext(f)[0].lower() == stem.lower():
                return os.path.join(r, f)


def import_mask(stem):
    name = "T_" + stem.replace("-", "_")
    path = TEX + "/" + name
    if not eal.does_asset_exist(path):
        t = unreal.AssetImportTask()
        t.filename = find_file(stem)
        t.destination_path = TEX
        t.destination_name = name
        t.automated = True
        t.replace_existing = True
        at.import_asset_tasks([t])
    tex = eal.load_asset(path)
    tex.set_editor_property("srgb", True)          # matches the Color sampler / white default
    tex.set_editor_property("max_texture_size", 2048)
    eal.save_loaded_asset(tex)
    return tex


def build_master():
    path = MAT + "/M_MayaGlass"
    if eal.does_asset_exist(path):
        m = eal.load_asset(path)
        if mel.get_num_material_expressions(m) > 0:
            return m
        eal.delete_asset(path)          # half-built from an earlier failed run
    white = unreal.load_asset("/Engine/EngineResources/WhiteSquareTexture")
    m = at.create_asset("M_MayaGlass", MAT, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    tlm = unreal.TranslucencyLightingMode
    mode = next((getattr(tlm, n) for n in ("TLM_SURFACE_FORWARD_SHADING", "TLM_SURFACE", "TLM_SURFACE_PER_PIXEL_LIGHTING") if hasattr(tlm, n)), None)
    log("translucency lighting modes:", [n for n in dir(tlm) if n.startswith("TLM")], "->", mode)
    if mode is not None:
        m.set_editor_property("translucency_lighting_mode", mode)
    E = lambda cls, x, y: mel.create_material_expression(m, cls, x, y)

    def tex_param(name, x, y):
        e = E(unreal.MaterialExpressionTextureSampleParameter2D, x, y)
        e.set_editor_property("parameter_name", name)
        e.set_editor_property("texture", white)
        return e

    def scalar(name, v, x, y):
        e = E(unreal.MaterialExpressionScalarParameter, x, y)
        e.set_editor_property("parameter_name", name)
        e.set_editor_property("default_value", v)
        return e

    def vector(name, c, x, y):
        e = E(unreal.MaterialExpressionVectorParameter, x, y)
        e.set_editor_property("parameter_name", name)
        e.set_editor_property("default_value", unreal.LinearColor(*c))
        return e

    def const(v, x, y):
        e = E(unreal.MaterialExpressionConstant, x, y)
        e.set_editor_property("r", v)
        return e

    def lerp(a, a_pin, b, b_pin, alpha, x, y):
        e = E(unreal.MaterialExpressionLinearInterpolate, x, y)
        mel.connect_material_expressions(a, a_pin, e, "A")
        mel.connect_material_expressions(b, b_pin, e, "B")
        mel.connect_material_expressions(alpha, "R", e, "Alpha")
        return e

    base = tex_param("BaseColorTex", -900, -300)
    tint = vector("Tint", (1, 1, 1, 1), -900, -50)
    mul = E(unreal.MaterialExpressionMultiply, -600, -200)
    mel.connect_material_expressions(base, "RGB", mul, "A")
    mel.connect_material_expressions(tint, "", mul, "B")
    refr = tex_param("RefractionTex", -900, 200)            # white = glass
    glass_col = vector("GlassColor", (0.02, 0.025, 0.03, 1), -600, 0)
    bc = lerp(mul, "", glass_col, "", refr, -300, -150)
    mel.connect_material_property(bc, "", unreal.MaterialProperty.MP_BASE_COLOR)
    op = lerp(const(1.0, -600, 350), "", scalar("GlassOpacity", 0.15, -600, 450), "", refr, -300, 300)
    mel.connect_material_property(op, "", unreal.MaterialProperty.MP_OPACITY)
    rough = lerp(scalar("Roughness", 0.5, -600, 600), "", scalar("GlassRoughness", 0.03, -600, 700), "", refr, -300, 550)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.recompile_material(m)
    eal.save_loaded_asset(m)
    log("created", path)
    return m


def build_mi(master, name, cfg):
    path = MAT + "/" + name
    mi = eal.load_asset(path) if eal.does_asset_exist(path) else at.create_asset(
        name, MAT, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mi, master)
    if cfg["base"]:
        mel.set_material_instance_texture_parameter_value(mi, "BaseColorTex", eal.load_asset(TEX + "/" + cfg["base"]))
    if cfg["refr"]:
        mel.set_material_instance_texture_parameter_value(mi, "RefractionTex", import_mask(cfg["refr"]))
    mel.set_material_instance_vector_parameter_value(mi, "Tint", unreal.LinearColor(1, 1, 1, 1))
    mel.set_material_instance_vector_parameter_value(mi, "GlassColor", unreal.LinearColor(0.02, 0.025, 0.03, 1))
    mel.set_material_instance_scalar_parameter_value(mi, "GlassOpacity", 0.15)
    mel.update_material_instance(mi)
    eal.save_loaded_asset(mi)
    return mi


def main():
    master = build_master()
    mis = {n: build_mi(master, n, c) for n, c in GLASS_MI.items()}
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    done = []
    meshes = set()
    for a in eas.get_all_level_actors():
        name = CANOPIES.get(a.get_actor_label())
        if not name:
            continue
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            sm = c.static_mesh
            if not sm:
                continue
            c.modify()
            for i in range(len(sm.static_materials)):
                sm.set_material(i, mis[name])
                c.set_material(i, mis[name])     # the scene import left per-component overrides
            meshes.add(sm)
            done.append(a.get_actor_label() + " -> " + name)
    for sm in meshes:
        eal.save_loaded_asset(sm)
    log("assigned:", done)
    # Sliders_24 carries a flat 15 x 23 m slider-panel mesh (Maya control UI) - hide only that mesh
    for a in eas.get_all_level_actors():
        if a.get_actor_label() == "Sliders_24":
            for c in a.get_components_by_class(unreal.StaticMeshComponent):
                c.modify()
                c.set_visibility(False, False)
                log("hid Sliders_24 panel mesh", c.get_name())
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    log("done")


main()
