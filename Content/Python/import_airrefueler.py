"""
AirRefueler - import Maya data from <Project>/Data into UE 5.6 (Interchange).

Run in the editor:  Output Log -> Cmd dropdown "Python" ->  import_airrefueler
   or: Tools > Execute Python Script... > Content/Python/import_airrefueler.py

What it does
  1. Imports the textures actually used by the Maya shaders -> /Game/AirRefueler/Textures
  2. Builds M_MayaPBR (BaseColor / Normal / Gloss->Roughness) + one MI per Maya material
  3. Imports Hose_N_drouge_INout_Animated.fbx as Skeletal Mesh + morph target + AnimSequence
       -> /Game/AirRefueler/Hose
  4. Creates level /Game/AirRefueler/Maps/L_RefuelScene and imports metosim_all.fbx into it
       (actors + hierarchy + Level Sequence for the baked transform animation)
       -> /Game/AirRefueler/Scene
  5. Replaces the grey imported materials with the MIs (mesh assets + level actors), saves.
"""
import os
import unreal

# ---------------------------------------------------------------- config
# stages can be picked on the command line:  py ".../import_airrefueler.py" textures materials
# (no arguments = run everything)
import sys
_stages = [a.lower() for a in sys.argv[1:]]
_on = lambda name: (not [a for a in _stages if a != "morphs"]) or (name in _stages)
DO_TEXTURES = _on("textures")
DO_MATERIALS = _on("materials") or _on("remap")
DO_HOSE = _on("hose")
DO_SCENE = _on("scene")
DO_REMAP = _on("remap")
SCENE_ALL_STATIC = "morphs" not in _stages   # add the word "morphs" to keep blendshape meshes as skeletal

ROOT = "/Game/AirRefueler"
TEX_PATH = ROOT + "/Textures"
MAT_PATH = ROOT + "/Materials"
HOSE_PATH = ROOT + "/Hose"
SCENE_PATH = ROOT + "/Scene"
LEVEL = ROOT + "/Maps/L_RefuelScene"

DATA = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()), "Data")
HOSE_FBX = os.path.join(DATA, "Hose_N_drouge_INout_Animated.fbx")
SCENE_FBX = os.path.join(DATA, "Senario_full_v06.ma", "metosim_all.fbx")

# Maya material -> textures (taken from the connections in Senario_full_v06.ma)
# base = diffuse, normal = tangent normal map, gloss = VRay glossiness (roughness = 1-gloss)
MATS = {
    "Wing_Main_Top":       dict(base="Top_Mian_Wing_Fliped_DFM", normal="Top_Mian_Wing_NRM", gloss="Top_Mian_Wing_Gloss"),
    "Wing_top":            dict(base="wing_top_DFM_Edited", gloss="BackWing_Gloss"),
    "wing_Bottom":         dict(base="wing_Bottom_DFM_Edited", gloss="body_Glossyness"),
    "small_wingA":         dict(base="small_wing_A_DFM_edited", gloss="small_wing_B_GLOS"),
    "small_wing_B":        dict(base="small_wing_B_DFM_Edited", gloss="small_wing_B_GLOS"),
    "Body_all":            dict(base="body_DFM_Edited", normal="body_NRM", gloss="body_Glossyness_N"),
    "body_clor_only2":     dict(base="767_ColorOnly", gloss="body_Glossyness"),
    "body_Bright":         dict(base="767_ColorOnly", gloss="body_Glossyness"),
    "pod":                 dict(base="pod_DFM_Edit", normal="pod_Normal", gloss="body_Glossyness"),
    "Drouge":              dict(base="Droug_dfm"),
    "Drouge3":             dict(base="Droug_dfm"),
    "Su_30_Body_VRay":     dict(base="Su-30_Body_Diffuse_Edited", gloss="Su-30_Body_Glossiness"),
    "Su_30_Detail_VRay":   dict(base="Su-30_Detail_Diffuse", gloss="Su-30_Detail_Glossiness"),
    "Su_30_Interior_VRay": dict(base="Su-30_Interior_Diffuse", gloss="Su-30_Interior_Glossiness"),
    "mat_Housing_VRay1":   dict(base="Housing_Diffuse_Edited", gloss="Housing_Glossiness"),   # Mirage 2000
    "Salon_VRay1":         dict(base="Salon_Diffuse", gloss="Salon_Glossiness"),              # Mirage 2000 cockpit
    "phong1":              dict(normal="Normal hose", tint=(0.04, 0.04, 0.04), roughness=0.6),  # hose FBX (file was 'naormal hose.jpg')
}

at = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
log = lambda *a: unreal.log("[AirRefueler] " + " ".join(str(x) for x in a))
warn = lambda *a: unreal.log_warning("[AirRefueler] " + " ".join(str(x) for x in a))


def safe(name):
    return name.strip().replace(" ", "_").replace("-", "_").replace("#", "")


def norm_key(name):
    n = name
    for p in ("MI_", "M_"):
        if n.startswith(p):
            n = n[len(p):]
    return n.lower()


# ---------------------------------------------------------------- 1. textures
def find_source_images():
    found = {}
    for root, _, files in os.walk(DATA):
        for f in files:
            stem, ext = os.path.splitext(f)
            if ext.lower() in (".tga", ".png", ".jpg", ".jpeg"):
                found.setdefault(stem.strip().lower(), os.path.join(root, f))
    return found


def import_textures():
    src = find_source_images()
    wanted = {}
    for m in MATS.values():
        for slot in ("base", "normal", "gloss"):
            if slot in m:
                wanted[m[slot]] = slot
    tasks, kinds = [], {}
    for stem, slot in wanted.items():
        path = src.get(stem.lower())
        if not path:
            warn("texture not found on disk:", stem)
            continue
        dest = "T_" + safe(stem)
        kinds[dest] = slot
        if eal.does_asset_exist(TEX_PATH + "/" + dest):
            continue
        t = unreal.AssetImportTask()
        t.filename = path
        t.destination_path = TEX_PATH
        t.destination_name = dest
        t.automated = True
        t.replace_existing = True
        t.save = False
        tasks.append(t)
    if tasks:
        log("importing", len(tasks), "textures (big TGAs, takes a while)...")
        at.import_asset_tasks(tasks)
    # fix texture settings
    for dest, slot in kinds.items():
        tex = eal.load_asset(TEX_PATH + "/" + dest)
        if not tex:
            warn("texture import failed:", dest)
            continue
        if slot == "normal":
            tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
            tex.set_editor_property("srgb", False)
        else:
            tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_DEFAULT)
            tex.set_editor_property("srgb", True)
        eal.save_loaded_asset(tex)


def tex(stem):
    return eal.load_asset(TEX_PATH + "/T_" + safe(stem)) if stem else None


# ---------------------------------------------------------------- 2. materials
def first_asset(paths):
    for p in paths:
        a = unreal.load_asset(p)
        if a:
            return a
    return None


def build_master():
    path = MAT_PATH + "/M_MayaPBR"
    if eal.does_asset_exist(path):
        return eal.load_asset(path)
    white = first_asset(["/Engine/EngineResources/WhiteSquareTexture", "/Engine/EngineMaterials/DefaultDiffuse"])
    flat = first_asset(["/Engine/EngineMaterials/FlatNormal", "/Engine/EngineMaterials/DefaultNormal"])
    m = at.create_asset("M_MayaPBR", MAT_PATH, unreal.Material, unreal.MaterialFactoryNew())

    def expr(cls, x, y):
        return mel.create_material_expression(m, cls, x, y)

    base = expr(unreal.MaterialExpressionTextureSampleParameter2D, -800, -300)
    base.set_editor_property("parameter_name", "BaseColorTex")
    base.set_editor_property("texture", white)
    tint = expr(unreal.MaterialExpressionVectorParameter, -800, -50)
    tint.set_editor_property("parameter_name", "Tint")
    tint.set_editor_property("default_value", unreal.LinearColor(1, 1, 1, 1))
    mul = expr(unreal.MaterialExpressionMultiply, -450, -200)
    mel.connect_material_expressions(base, "RGB", mul, "A")
    mel.connect_material_expressions(tint, "", mul, "B")
    mel.connect_material_property(mul, "", unreal.MaterialProperty.MP_BASE_COLOR)

    nrm = expr(unreal.MaterialExpressionTextureSampleParameter2D, -800, 150)
    nrm.set_editor_property("parameter_name", "NormalTex")
    nrm.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    nrm.set_editor_property("texture", flat)
    mel.connect_material_property(nrm, "RGB", unreal.MaterialProperty.MP_NORMAL)

    gl = expr(unreal.MaterialExpressionTextureSampleParameter2D, -800, 450)
    gl.set_editor_property("parameter_name", "GlossTex")
    gl.set_editor_property("texture", white)
    inv = expr(unreal.MaterialExpressionOneMinus, -500, 450)
    mel.connect_material_expressions(gl, "R", inv, "")
    rough = expr(unreal.MaterialExpressionScalarParameter, -500, 650)
    rough.set_editor_property("parameter_name", "Roughness")
    rough.set_editor_property("default_value", 0.5)
    use = expr(unreal.MaterialExpressionScalarParameter, -500, 750)
    use.set_editor_property("parameter_name", "UseGlossTex")
    use.set_editor_property("default_value", 0.0)
    lerp = expr(unreal.MaterialExpressionLinearInterpolate, -250, 550)
    mel.connect_material_expressions(rough, "", lerp, "A")
    mel.connect_material_expressions(inv, "", lerp, "B")
    mel.connect_material_expressions(use, "", lerp, "Alpha")
    mel.connect_material_property(lerp, "", unreal.MaterialProperty.MP_ROUGHNESS)

    met = expr(unreal.MaterialExpressionScalarParameter, -250, 300)
    met.set_editor_property("parameter_name", "Metallic")
    met.set_editor_property("default_value", 0.0)
    mel.connect_material_property(met, "", unreal.MaterialProperty.MP_METALLIC)

    mel.recompile_material(m)
    eal.save_loaded_asset(m)
    return m


def build_instances(master):
    out = {}
    for name, cfg in MATS.items():
        path = MAT_PATH + "/MI_" + safe(name)
        mi = eal.load_asset(path) if eal.does_asset_exist(path) else at.create_asset(
            "MI_" + safe(name), MAT_PATH, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        mel.set_material_instance_parent(mi, master)
        b, n, g = tex(cfg.get("base")), tex(cfg.get("normal")), tex(cfg.get("gloss"))
        if b:
            mel.set_material_instance_texture_parameter_value(mi, "BaseColorTex", b)
        if n:
            mel.set_material_instance_texture_parameter_value(mi, "NormalTex", n)
        if g:
            mel.set_material_instance_texture_parameter_value(mi, "GlossTex", g)
            mel.set_material_instance_scalar_parameter_value(mi, "UseGlossTex", 1.0)
        if "tint" in cfg:
            mel.set_material_instance_vector_parameter_value(mi, "Tint", unreal.LinearColor(*cfg["tint"], 1.0))
        if "roughness" in cfg:
            mel.set_material_instance_scalar_parameter_value(mi, "Roughness", cfg["roughness"])
        mel.update_material_instance(mi)
        eal.save_loaded_asset(mi)
        out[name.lower()] = mi
    log("material instances:", len(out))
    return out


# ---------------------------------------------------------------- 3/4. FBX via Interchange
def interchange_params(pipeline=None):
    p = unreal.ImportAssetParameters()
    p.is_automated = True
    if pipeline is not None:
        p.override_pipelines.append(unreal.SoftObjectPath(pipeline.get_path_name()))
    return p


def import_hose():
    if not os.path.exists(HOSE_FBX):
        warn("missing", HOSE_FBX)
        return
    im = unreal.InterchangeManager.get_interchange_manager_scripted()
    src = im.create_source_data(HOSE_FBX)
    pl = unreal.InterchangeGenericAssetsPipeline()
    # blendshape-only mesh (no skin) -> must be skeletal to keep the morph target + its animation
    pl.common_meshes_properties.force_all_mesh_as_type = unreal.InterchangeForceMeshType.IFMT_SKELETAL_MESH
    pl.mesh_pipeline.import_morph_targets = True
    pl.animation_pipeline.import_animations = True
    log("importing hose:", HOSE_FBX)
    ok = im.import_asset(HOSE_PATH, src, interchange_params(pl))
    log("hose import ok =", ok)


def save_all():
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)


def scene_pipelines():
    """Project copy of the default FBX scene pipeline with every mesh forced to Static Mesh.
    The Maya scene has 173 blendshape meshes (jet nozzle petals); as skeletal meshes they cost
    172 skeletons + GPU skin cache and the first import ended in a GPU crash."""
    dst = ROOT + "/Pipelines/PL_SceneAssets_Static"
    if not eal.does_asset_exist(dst):
        src = next(p for p in ("/Interchange/Pipelines/DefaultFBXOBJSceneAssetsPipeline",
                               "/Interchange/Pipelines/DefaultSceneAssetsPipeline") if eal.does_asset_exist(p))
        log("scene pipeline copied from", src)
        eal.duplicate_asset(src, dst)
    pl = eal.load_asset(dst)
    pl.common_meshes_properties.force_all_mesh_as_type = unreal.InterchangeForceMeshType.IFMT_STATIC_MESH
    eal.save_loaded_asset(pl)
    level_pl = "/Interchange/Pipelines/DefaultSceneLevelPipeline.DefaultSceneLevelPipeline"
    return [unreal.SoftObjectPath(pl.get_path_name()), unreal.SoftObjectPath(level_pl)]


def import_scene():
    if not os.path.exists(SCENE_FBX):
        warn("missing", SCENE_FBX)
        return
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if eal.does_asset_exist(LEVEL):
        warn("level already exists, skipping scene import (delete", LEVEL, "and", SCENE_PATH, "to re-import)")
        les.load_level(LEVEL)
        return
    les.new_level(LEVEL)
    im = unreal.InterchangeManager.get_interchange_manager_scripted()
    src = im.create_source_data(SCENE_FBX)
    p = unreal.ImportAssetParameters()
    p.is_automated = True
    if SCENE_ALL_STATIC:
        for sp in scene_pipelines():
            p.override_pipelines.append(sp)
    log("importing scene (703 meshes), all static =", SCENE_ALL_STATIC)
    ok = im.import_scene(SCENE_PATH, src, p)
    log("scene import ok =", ok)
    log("saving imported assets + level...")
    save_all()
    les.save_current_level()
    log("scene saved")


# ---------------------------------------------------------------- 5. material remap
def remap(mis):
    hits = 0
    for p in eal.list_assets(ROOT, recursive=True, include_folder=False):
        if p.startswith(MAT_PATH) or p.startswith(TEX_PATH):
            continue
        cls = str(eal.find_asset_data(p).asset_class_path.asset_name)
        if cls == "StaticMesh":
            sm = eal.load_asset(p)
            changed = False
            for i, s in enumerate(sm.static_materials):
                cand = [str(s.material_slot_name)] + ([s.material_interface.get_name()] if s.material_interface else [])
                mi = next((mis[norm_key(c)] for c in cand if norm_key(c) in mis), None)
                if mi and s.material_interface != mi:
                    sm.set_material(i, mi)
                    changed = True
                    hits += 1
        elif cls == "SkeletalMesh":
            sk = eal.load_asset(p)
            mats = []
            changed = False
            for s in sk.get_editor_property("materials"):
                mats.append(s)
                mint = s.get_editor_property("material_interface")
                cand = [str(s.get_editor_property("material_slot_name"))] + ([mint.get_name()] if mint else [])
                mi = next((mis[norm_key(c)] for c in cand if norm_key(c) in mis), None)
                if mi and mint != mi:
                    s.set_editor_property("material_interface", mi)
                    changed = True
                    hits += 1
            if changed:
                sk.set_editor_property("materials", mats)
    # per-actor overrides in the open level
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in eas.get_all_level_actors():
        for c in a.get_components_by_class(unreal.MeshComponent):
            for i, m in enumerate(c.get_materials()):
                if m and norm_key(m.get_name()) in mis and m != mis[norm_key(m.get_name())]:
                    c.set_material(i, mis[norm_key(m.get_name())])
                    hits += 1
    log("material slots remapped:", hits)
    save_all()


def report():
    seqs = [p for p in eal.list_assets(ROOT, True, False)
            if str(eal.find_asset_data(p).asset_class_path.asset_name) == "LevelSequence"]
    anims = [p for p in eal.list_assets(ROOT, True, False)
             if str(eal.find_asset_data(p).asset_class_path.asset_name) == "AnimSequence"]
    log("LevelSequences:", seqs or "NONE - see notes (Sequencer > Import FBX fallback)")
    log("AnimSequences:", anims or "NONE")


def main():
    log("Data folder:", DATA, "| stages:", _stages or "all")
    if DO_TEXTURES:
        import_textures()
    mis = {}
    if DO_MATERIALS:
        mis = build_instances(build_master())
    if DO_HOSE:
        import_hose()
    if DO_SCENE:
        import_scene()
    if DO_REMAP and mis:
        remap(mis)
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    report()
    log("done.")


try:
    main()
except Exception:
    import traceback
    unreal.log_error("[AirRefueler] FAILED\n" + traceback.format_exc())
    raise
