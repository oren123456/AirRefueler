"""Parachute collides only with WorldDynamic (= the Col_* capsules on the Mirage); it ignores the tanker, pods and the Mirage render meshes."""
import unreal
eal = unreal.EditorAssetLibrary
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem); SDL = unreal.SubobjectDataBlueprintFunctionLibrary
hose = eal.load_asset("/Game/AirRefueler/Sim/BP_RefuelHose")
for h in sds.k2_gather_subobject_data_for_blueprint(hose):
    o = SDL.get_object(SDL.get_data(h))
    if o and o.get_name().startswith("Parachute"):
        o.set_collision_profile_name("Custom")
        o.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
        o.set_collision_object_type(unreal.CollisionChannel.ECC_PHYSICS_BODY)
        o.set_collision_response_to_all_channels(unreal.CollisionResponseType.ECR_IGNORE)
        o.set_collision_response_to_channel(unreal.CollisionChannel.ECC_WORLD_DYNAMIC, unreal.CollisionResponseType.ECR_BLOCK)
        unreal.log("[ChuteColl] set on " + o.get_name())
unreal.BlueprintEditorLibrary.compile_blueprint(hose); eal.save_loaded_asset(hose)
