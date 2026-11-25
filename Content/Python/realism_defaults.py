"""BP_RefuelHose realism defaults. argv: TurbAmp BowStrength (defaults 1.0 200). Sets the Blueprint CDO and the level
instance, compiles and saves."""
import unreal, sys
ta = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
bs = float(sys.argv[2]) if len(sys.argv) > 2 else 200.0
eal = unreal.EditorAssetLibrary
bp = eal.load_asset("/Game/AirRefueler/Sim/BP_RefuelHose")
cdo = unreal.get_default_object(bp.generated_class())
cdo.set_editor_property("TurbAmp", ta); cdo.set_editor_property("BowStrength", bs)
eal.save_loaded_asset(bp, False)
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if a.get_class() == bp.generated_class():
        a.set_editor_property("TurbAmp", ta); a.set_editor_property("BowStrength", bs)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
unreal.log("[Realism] TurbAmp=%s BowStrength=%s cdo=(%s,%s)" % (ta, bs, cdo.get_editor_property("TurbAmp"), cdo.get_editor_property("BowStrength")))
