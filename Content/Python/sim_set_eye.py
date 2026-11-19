"""Move BP_MiragePawn.PilotCam to the pilot's eye point.
Front seat (Pilot_s_Seat): cushion top z≈-294, seat-back/headrest front face y≈-9668, headrest top z≈-204.
Eye = 75 cm above cushion, 18 cm in front of the headrest, on the centreline -> world (1683.5, -9650, -219)."""
import unreal
EYE = unreal.Vector(1683.5, -9650.0, -227.0)
ROOT = unreal.Vector(1682.6, -9933.1, -224.0)   # pawn / Mirage_2000N location at start
bp = unreal.EditorAssetLibrary.load_asset("/Game/AirRefueler/Sim/BP_MiragePawn")
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem); SDL = unreal.SubobjectDataBlueprintFunctionLibrary
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    o = SDL.get_object(SDL.get_data(h))
    if isinstance(o, unreal.CameraComponent):
        o.set_editor_property("relative_location", EYE - ROOT)
        unreal.log("[SimEye] PilotCam relative -> %s" % (EYE - ROOT))
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
unreal.EditorAssetLibrary.save_loaded_asset(bp)
