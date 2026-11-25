"""Cockpit audio: import Data/Generated/Audio/*.wav (Tools/cockpit_audio.py) into Sim/Audio, loop the A_* beds, and build
BP_CockpitAudio (2D AudioComponents ECS/Air/Engine/Breath/Wake/RadioHiss; graph in sim_dsl/cockpit_audio.lisp) + place it."""
import unreal, os, glob
eal = unreal.EditorAssetLibrary; at = unreal.AssetToolsHelpers.get_asset_tools()
D = "/Game/AirRefueler/Sim/Audio"
root = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
log = lambda s: unreal.log("[Audio] " + s)
for f in sorted(glob.glob(os.path.join(root, "Data", "Generated", "Audio", "*.wav"))):
    n = os.path.splitext(os.path.basename(f))[0]
    t = unreal.AssetImportTask(); t.filename = f; t.destination_path = D; t.destination_name = n
    t.automated = True; t.replace_existing = True; t.save = True
    at.import_asset_tasks([t])
    w = eal.load_asset(D + "/" + n)
    w.set_editor_property("looping", n.startswith("A_"))
    eal.save_loaded_asset(w)
log("imported %s" % eal.list_assets(D, False))
# per-bed SoundClasses (volume/pitch driven at runtime through SM_Cockpit class overrides)
for n in ("Engine", "Air", "Wake", "Breath"):
    if not eal.does_asset_exist(D + "/SC_" + n):
        at.create_asset("SC_" + n, D, unreal.SoundClass, unreal.SoundClassFactory())
    w = eal.load_asset(D + "/A_" + n); w.set_editor_property("sound_class_object", eal.load_asset(D + "/SC_" + n)); eal.save_loaded_asset(w)
    eal.save_asset(D + "/SC_" + n)
if not eal.does_asset_exist(D + "/SM_Cockpit"):
    at.create_asset("SM_Cockpit", D, unreal.SoundMix, unreal.SoundMixFactory())
eal.save_asset(D + "/SM_Cockpit")
bp_path = D + "/BP_CockpitAudio"
if not eal.does_asset_exist(bp_path):
    f = unreal.BlueprintFactory(); f.set_editor_property("parent_class", unreal.Actor)
    at.create_asset("BP_CockpitAudio", D, unreal.Blueprint, f)
bp = eal.load_asset(bp_path)
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem); L = unreal.SubobjectDataBlueprintFunctionLibrary
handles = sds.k2_gather_subobject_data_for_blueprint(bp)
have = {str(L.get_variable_name(L.get_data(h))): h for h in handles}
beds = {"ECS": 0.3, "Air": 1.0, "Engine": 1.0, "Breath": 0.22, "Wake": 1.0}
for name, vol in beds.items():
    if name in have: h = have[name]
    else:
        p = unreal.AddNewSubobjectParams(parent_handle=handles[0], new_class=unreal.AudioComponent, blueprint_context=bp)
        h, why = sds.add_new_subobject(p)
        sds.rename_subobject(h, unreal.Text(name))
    c = L.get_object(L.get_data(h))
    c.set_editor_property("sound", eal.load_asset(D + "/A_" + name))
    c.set_editor_property("allow_spatialization", False)
    c.set_editor_property("auto_activate", True)
    c.set_editor_property("volume_multiplier", vol)
if "RadioHiss" in have:   # unused bed from the first version: keep silent
    L.get_object(L.get_data(have["RadioHiss"])).set_editor_property("auto_activate", False)
unreal.BlueprintEditorLibrary.compile_blueprint(bp); eal.save_loaded_asset(bp)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if not [a for a in eas.get_all_level_actors() if a.get_class().get_name().startswith("BP_CockpitAudio")]:
    a = eas.spawn_actor_from_class(bp.generated_class(), unreal.Vector(0, 0, 0)); a.set_actor_label("CockpitAudio")
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
log("components %s" % [str(L.get_variable_name(L.get_data(h))) for h in sds.k2_gather_subobject_data_for_blueprint(bp)])
log("done")
