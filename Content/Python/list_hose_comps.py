import unreal
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem); SDL = unreal.SubobjectDataBlueprintFunctionLibrary
bp = unreal.EditorAssetLibrary.load_asset("/Game/AirRefueler/Sim/BP_RefuelHose")
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    d = SDL.get_data(h); o = SDL.get_object(d)
    if not o: continue
    p = o.get_attach_parent() if isinstance(o, unreal.SceneComponent) else None
    ph = SDL.get_data(SDL.get_parent_handle(d)) if hasattr(SDL, "get_parent_handle") else None
    unreal.log("[HoseComps] %s (%s) attachParent=%s isRoot=%s rel=%s" % (o.get_name(), o.get_class().get_name(), p.get_name() if p else None, SDL.is_root_component(d) if hasattr(SDL,"is_root_component") else "?", o.get_editor_property("relative_location") if isinstance(o, unreal.SceneComponent) else ""))
