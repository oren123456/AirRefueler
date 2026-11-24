"""Cap how fast physics pushes the parachute out of an overlap (teleports / fast closures)."""
import unreal
eal = unreal.EditorAssetLibrary
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem); SDL = unreal.SubobjectDataBlueprintFunctionLibrary
hose = eal.load_asset("/Game/AirRefueler/Sim/BP_RefuelHose")
for h in sds.k2_gather_subobject_data_for_blueprint(hose):
    o = SDL.get_object(SDL.get_data(h))
    if o and o.get_name().startswith("Parachute"):
        bi = o.get_editor_property("body_instance")
        for k, v in (("override_max_depenetration_velocity", True), ("max_depenetration_velocity", 150.0)):
            try: bi.set_editor_property(k, v); unreal.log("[ChuteDepen] %s=%s" % (k, v))
            except Exception as e: unreal.log("[ChuteDepen] %s: %s" % (k, e))
        o.set_editor_property("body_instance", bi)
unreal.BlueprintEditorLibrary.compile_blueprint(hose); eal.save_loaded_asset(hose)
