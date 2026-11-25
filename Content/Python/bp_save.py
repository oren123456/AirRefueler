"""Compile + save the sim Blueprints and log their status."""
import unreal
for p in ("/Game/AirRefueler/Sim/BP_RefuelHose", "/Game/AirRefueler/Sim/HUD/BP_HUDDriver", "/Game/AirRefueler/Sim/Audio/BP_CockpitAudio"):
    bp = unreal.load_asset(p); unreal.BlueprintEditorLibrary.compile_blueprint(bp); unreal.EditorAssetLibrary.save_loaded_asset(bp)
    unreal.log("[BPSave] %s %s" % (p.split("/")[-1], bp.get_editor_property("status")))
