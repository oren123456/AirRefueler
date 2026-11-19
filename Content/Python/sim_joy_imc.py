"""Enhanced Input mapping for the RawInput joystick axes (unmapped analog keys always read 0 with EnhancedPlayerInput).
Creates IA_JoyAxis1..5 (Axis1D) + IMC_Joystick in /Game/AirRefueler/Sim/Input, and sets the Extreme 3D Pro axis map
RawInput (Config/DefaultInput.ini) routes the Extreme 3D Pro axes to these engine analog keys: X->Gamepad_Special_Left_X, Y->Gamepad_Special_Left_Y, twist->Gamepad_LeftTriggerAxis, throttle->Gamepad_RightTriggerAxis."""
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
KEYS = {1: "Gamepad_Special_Left_X", 2: "Gamepad_Special_Left_Y", 3: "Gamepad_LeftTriggerAxis", 4: "Gamepad_RightTriggerAxis"}
for i in range(1, 5):
    ia = get_or_make("IA_JoyAxis%d" % i, unreal.InputAction)
    ia.set_editor_property("value_type", unreal.InputActionValueType.AXIS1D)
    eal.save_loaded_asset(ia)
    k = unreal.Key(); k.import_text(KEYS[i])
    imc.map_key(ia, k)
    log("mapped", k.export_text(), "->", ia.get_name())
eal.save_loaded_asset(imc)
vals = KEYS
log("done", vals)
