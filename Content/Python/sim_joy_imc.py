"""Enhanced Input mapping for the RawInput joystick axes (unmapped analog keys always read 0 with EnhancedPlayerInput).
Creates IA_JoyAxis1..5 (Axis1D) + IMC_Joystick in /Game/AirRefueler/Sim/Input, and sets the Extreme 3D Pro axis map
(from ShowDebug RawInput: Axis1=Y, Axis2=X, Axis3=hat, Axis4=Rz twist, Axis5=slider throttle)."""
import unreal
P = "/Game/AirRefueler/Sim/Input"
eal = unreal.EditorAssetLibrary; at = unreal.AssetToolsHelpers.get_asset_tools()
log = lambda *x: unreal.log("[JoyIMC] " + " ".join(str(v) for v in x))
def get_or_make(name, cls):
    path = P + "/" + name
    if eal.does_asset_exist(path):
        return eal.load_asset(path)
    return at.create_asset(name, P, cls, None)
imc = get_or_make("IMC_Joystick", unreal.InputMappingContext)
try: imc.unmap_all()
except Exception as e: log("unmap_all", e)
for i in range(1, 6):
    ia = get_or_make("IA_JoyAxis%d" % i, unreal.InputAction)
    ia.set_editor_property("value_type", unreal.InputActionValueType.AXIS1D)
    eal.save_loaded_asset(ia)
    k = unreal.Key(); k.import_text("GenericUSBController_Axis%d" % i)
    imc.map_key(ia, k)
    log("mapped", k.export_text(), "->", ia.get_name())
eal.save_loaded_asset(imc)
bp = eal.load_asset("/Game/AirRefueler/Sim/BP_MiragePawn")
vals = dict(JoyStrafeAxis=2, JoyVertAxis=1, JoyTwistAxis=4, JoyThrottleAxis=5)
cdo = unreal.get_default_object(bp.generated_class())
for k, v in vals.items(): cdo.set_editor_property(k, v)
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if a.get_actor_label() == "SimPlayer_Mirage":
        for k, v in vals.items(): a.set_editor_property(k, v)
eal.save_loaded_asset(bp)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
log("done", vals)
