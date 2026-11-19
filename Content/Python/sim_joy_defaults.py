"""Joystick defaults on BP_MiragePawn (Logitech Extreme 3D Pro guess: X=1, Y=2, twist Rz=4, throttle slider=5)."""
import unreal
bp = unreal.EditorAssetLibrary.load_asset("/Game/AirRefueler/Sim/BP_MiragePawn")
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
cdo = unreal.get_default_object(bp.generated_class())
vals = dict(JoyStrafeAxis=1, JoyVertAxis=2, JoyTwistAxis=4, JoyThrottleAxis=5,
            JoyInvertStrafe=False, JoyInvertVert=False, JoyInvertThrottle=True, JoyInvertTwist=False,
            JoyDebug=False, JoyDeadzone=0.06)
for k, v in vals.items():
    cdo.set_editor_property(k, v)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in eas.get_all_level_actors():
    if a.get_actor_label() == "SimPlayer_Mirage":
        for k, v in vals.items():
            a.set_editor_property(k, v)
unreal.EditorAssetLibrary.save_loaded_asset(bp)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
unreal.log("[JoyDefaults] set " + str(vals))
