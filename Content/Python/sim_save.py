import unreal
bp = unreal.EditorAssetLibrary.load_asset("/Game/AirRefueler/Sim/BP_MiragePawn")
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
unreal.EditorAssetLibrary.save_directory("/Game/AirRefueler/Sim", only_if_is_dirty=False)
unreal.log("[SimSave] compiled + saved")
