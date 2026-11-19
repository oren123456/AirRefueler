"""Joystick tuning defaults on BP_MiragePawn + the placed SimPlayer_Mirage (Logitech Extreme 3D Pro)."""
import unreal
bp = unreal.EditorAssetLibrary.load_asset("/Game/AirRefueler/Sim/BP_MiragePawn")
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
cdo = unreal.get_default_object(bp.generated_class())
vals = dict(JoyInvertStrafe=False, JoyInvertVert=True, JoyInvertThrottle=True, JoyInvertTwist=False,
            JoyDebug=False, JoyDeadzone=0.06)
for k, v in vals.items():
    cdo.set_editor_property(k, v)
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if a.get_actor_label() == "SimPlayer_Mirage":
        for k, v in vals.items():
            a.set_editor_property(k, v)
unreal.EditorAssetLibrary.save_loaded_asset(bp)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
unreal.log("[JoyDefaults] set " + str(vals))
