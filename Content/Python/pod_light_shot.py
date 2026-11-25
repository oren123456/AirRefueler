import unreal, time
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem); ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
h = next(a for a in eas.get_all_level_actors() if a.get_actor_label() == "SimHose_LeftPod")
L = h.get_actor_location()
cam = L + unreal.Vector(-150.0, -260.0, -110.0)
ues.set_level_viewport_camera_info(cam, unreal.MathLibrary.find_look_at_rotation(cam, L + unreal.Vector(0, 40, -20)))
st = {"t": time.time(), "h": None}
def tick(dt):
    if time.time() - st["t"] > 1.5:
        unreal.SystemLibrary.execute_console_command(None, "HighResShot 1"); unreal.unregister_slate_post_tick_callback(st["h"]); unreal.log("[PodShot] shot")
st["h"] = unreal.register_slate_post_tick_callback(tick)
