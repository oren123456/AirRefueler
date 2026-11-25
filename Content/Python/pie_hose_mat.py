import unreal, time
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if unreal.EditorLevelLibrary.get_game_world() is None: les.editor_request_begin_play()
st = {"t0": None, "h": None}
def tick(dt):
    w = unreal.EditorLevelLibrary.get_game_world()
    if w is None: return
    if st["t0"] is None: st["t0"] = time.time()
    if time.time() - st["t0"] < 1.0: return
    unreal.unregister_slate_post_tick_callback(st["h"])
    for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor):
        if "BP_RefuelHose" in a.get_class().get_name():
            c = a.get_component_by_class(unreal.CableComponent)
            unreal.log("[PIEHoseMat] mat=%s used=%s tile=%s segs=%s width=%s sides=%s" % (c.get_material(0), [m.get_name() for m in c.get_materials()], c.get_editor_property("tile_material"), c.get_editor_property("num_segments"), c.get_editor_property("cable_width"), c.get_editor_property("num_sides")))
    les.editor_request_end_play()
st["h"] = unreal.register_slate_post_tick_callback(tick)
