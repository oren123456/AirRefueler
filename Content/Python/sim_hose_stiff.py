"""Stiffer refuel hose: fewer, longer cable segments, stiffness constraint on, more solver iterations, less sag."""
import unreal
eal = unreal.EditorAssetLibrary
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem); SDL = unreal.SubobjectDataBlueprintFunctionLibrary
VALS = dict(num_segments=12, solver_iterations=24, enable_stiffness=True, cable_gravity_scale=0.35,
            substep_time=0.005, use_substepping=True, cable_force=unreal.Vector(0, -600, 0))
def apply(c, tag):
    for k, v in VALS.items():
        try: c.set_editor_property(k, v)
        except Exception as e: unreal.log("[HoseStiff] %s %s: %s" % (tag, k, e))
hose = eal.load_asset("/Game/AirRefueler/Sim/BP_RefuelHose")
for h in sds.k2_gather_subobject_data_for_blueprint(hose):
    o = SDL.get_object(SDL.get_data(h))
    if isinstance(o, unreal.CableComponent):
        apply(o, "template")
unreal.BlueprintEditorLibrary.compile_blueprint(hose); eal.save_loaded_asset(hose)
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if a.get_class().get_name().startswith("BP_RefuelHose"):
        for c in a.get_components_by_class(unreal.CableComponent):
            c.modify(); apply(c, a.get_actor_label())
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
unreal.log("[HoseStiff] done %s" % VALS)
