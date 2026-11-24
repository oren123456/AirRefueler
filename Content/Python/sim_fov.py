import unreal, sys
FOV = float(sys.argv[1]) if len(sys.argv) > 1 else 105.0
bp = unreal.EditorAssetLibrary.load_asset("/Game/AirRefueler/Sim/BP_MiragePawn")
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem); SDL = unreal.SubobjectDataBlueprintFunctionLibrary
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    o = SDL.get_object(SDL.get_data(h))
    if isinstance(o, unreal.CameraComponent):
        unreal.log("[SimFOV] %s -> %s" % (o.get_editor_property("field_of_view"), FOV))
        o.set_editor_property("field_of_view", FOV)
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
unreal.EditorAssetLibrary.save_loaded_asset(bp)
