"""Parachute is now driven by BP_RefuelHose's own integrator + basket contact model (no Chaos simulation):
simulate off, collision QueryOnly ignoring everything (hulls stay in the asset for traces/debug).
Resaves the BP and deletes the last redirectors left by the content reorganisation."""
import unreal
eal = unreal.EditorAssetLibrary
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem); SDL = unreal.SubobjectDataBlueprintFunctionLibrary
log = lambda s: unreal.log("[ChuteKin] " + s)
hose = eal.load_asset("/Game/AirRefueler/Sim/BP_RefuelHose")
for h in sds.k2_gather_subobject_data_for_blueprint(hose):
    o = SDL.get_object(SDL.get_data(h))
    if o and o.get_name().startswith("Parachute"):
        o.set_simulate_physics(False)
        o.set_collision_profile_name("Custom")
        o.set_collision_enabled(unreal.CollisionEnabled.QUERY_ONLY)
        o.set_collision_response_to_all_channels(unreal.CollisionResponseType.ECR_IGNORE)
        log("parachute %s sm=%s" % (o.get_name(), o.get_editor_property("static_mesh").get_path_name()))
    if o and o.get_name().startswith("Body"):
        log("body sm=%s" % o.get_editor_property("static_mesh").get_path_name())
unreal.BlueprintEditorLibrary.compile_blueprint(hose)
eal.save_asset("/Game/AirRefueler/Sim/BP_RefuelHose", only_if_is_dirty=False)
ar = unreal.AssetRegistryHelpers.get_asset_registry()
opts = unreal.AssetRegistryDependencyOptions(include_soft_package_references=True, include_hard_package_references=True)
for ad in ar.get_assets_by_path("/Game/AirRefueler", True):
    if str(ad.asset_class_path.asset_name) == "ObjectRedirector":
        refs = [str(x) for x in (ar.get_referencers(ad.package_name, opts) or []) if str(x).startswith("/Game")]
        if refs: log("redirector %s still referenced by %s" % (ad.package_name, refs))
        else: log("delete redirector %s -> %s" % (ad.package_name, eal.delete_asset(str(ad.package_name))))
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
log("done")
