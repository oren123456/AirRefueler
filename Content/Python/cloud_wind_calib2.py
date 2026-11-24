"""Calibrate cloud wind: editor viewport camera straight down from the Mirage, Layout_WindControls=(0,W,0,1),
two HighResShots 2 s apart; logs camera Z and times. argv: W."""
import unreal, time, sys
W = float(sys.argv[1]) if len(sys.argv) > 1 else 10.0
mel = unreal.MaterialEditingLibrary
mi = unreal.load_asset("/Game/AirRefueler/Maps/MI_VolumetricCloud_Refuel")
mel.set_material_instance_vector_parameter_value(mi, "Layout_WindControls", unreal.LinearColor(0.0, W, 0.0, 1.0))
mel.update_material_instance(mi)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
m = next(a for a in eas.get_all_level_actors() if a.get_actor_label() == "SimPlayer_Mirage")
p = m.get_actor_location(); p = unreal.Vector(p.x, p.y, 1000000.0)  # 16 km altitude, ~11.5 km above cloud tops
ues.set_level_viewport_camera_info(p, unreal.Rotator(roll=0.0, pitch=-90.0, yaw=90.0))
log = lambda s: unreal.log("[WindCalib2] " + s)
log("cam z=%.0f W=%s" % (p.z, W))
st = {"t0": time.time(), "step": 0, "h": None}
def tick(dt):
    t = time.time() - st["t0"]
    if st["step"] == 0 and t > 2.0:
        unreal.SystemLibrary.execute_console_command(None, "HighResShot 1"); log("shot1 t=%.3f" % t); st["step"] = 1
    elif st["step"] == 1 and t > 6.0:
        unreal.SystemLibrary.execute_console_command(None, "HighResShot 1"); log("shot2 t=%.3f" % t); st["step"] = 2
        unreal.unregister_slate_post_tick_callback(st["h"])
st["h"] = unreal.register_slate_post_tick_callback(tick)
