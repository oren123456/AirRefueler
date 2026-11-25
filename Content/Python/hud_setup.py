"""HUD step 1: font atlas texture, MPC_HUD (data from BP_HUDDriver -> M_HUD on the combiner), BP_HUDDriver actor in
the level. Re-runnable."""
import os, unreal
HUD = "/Game/AirRefueler/Sim/HUD"
eal = unreal.EditorAssetLibrary; at = unreal.AssetToolsHelpers.get_asset_tools()
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
log = lambda s: unreal.log("[HUD] " + s)
root = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())

t = unreal.AssetImportTask(); t.filename = os.path.join(root, "Data", "Generated", "T_HUDFont.png")
t.destination_path = HUD; t.destination_name = "T_HUDFont"; t.automated = True; t.replace_existing = True; t.save = True
at.import_asset_tasks([t])
tex = eal.load_asset(HUD + "/T_HUDFont")
tex.set_editor_property("srgb", False)
tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_GRAYSCALE)
tex.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_UI)
eal.save_loaded_asset(tex)

mp = HUD + "/MPC_HUD"
mpc = eal.load_asset(mp) if eal.does_asset_exist(mp) else at.create_asset("MPC_HUD", HUD, unreal.MaterialParameterCollection, unreal.MaterialParameterCollectionFactoryNew())
def vp(n, v):
    p = unreal.CollectionVectorParameter(); p.set_editor_property("parameter_name", n); p.set_editor_property("default_value", unreal.LinearColor(*v)); return p
WANT = [
    vp("AFwd", (0, 1, 0, 0)),          # aircraft nose direction (world)
    vp("AUp", (0, 0, 1, 0)),           # aircraft up (world)
    vp("Vel", (0, 0, 0, 0)),           # velocity relative to the tanker, cm/s (world)
    vp("D0", (285, 19700, 1, 2)),      # IAS kt, altitude ft, G, hose state
    vp("D1", (0, 24, 0, 0)),           # closure m/s, range probe->basket m, fuel kg, fuel flowing 0/1
    vp("D2", (0, 0, 5.5, 0)),          # refuel aid shown 0/1 (H), acceleration-chevron offset deg, incidence deg, -
]
# append missing parameters only: replacing the list would give existing ones new IDs and break material refs
cur = list(mpc.get_editor_property("vector_parameters"))
have = [str(x.get_editor_property("parameter_name")) for x in cur]
cur += [x for x in WANT if str(x.get_editor_property("parameter_name")) not in have]
mpc.set_editor_property("vector_parameters", cur)
eal.save_loaded_asset(mpc)

bp_path = HUD + "/BP_HUDDriver"
if not eal.does_asset_exist(bp_path):
    f = unreal.BlueprintFactory(); f.set_editor_property("parent_class", unreal.Actor)
    at.create_asset("BP_HUDDriver", HUD, unreal.Blueprint, f)
bp = eal.load_asset(bp_path)
if not any(a.get_actor_label() == "HUDDriver" for a in eas.get_all_level_actors()):
    a = eas.spawn_actor_from_class(bp.generated_class(), unreal.Vector(0, 0, 0)); a.set_actor_label("HUDDriver")
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
log("done")
