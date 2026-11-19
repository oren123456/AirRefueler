import unreal
for p in ("/Game/AirRefueler/Sim/BP_MiragePawn", "/Game/AirRefueler/Sim/BP_RefuelHose"):
    unreal.BlueprintEditorLibrary.compile_blueprint(unreal.EditorAssetLibrary.load_asset(p))
unreal.EditorAssetLibrary.save_directory("/Game/AirRefueler/Sim", only_if_is_dirty=False)
unreal.log("[SimSave] compiled + saved")
