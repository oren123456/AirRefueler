"""Only two collision bodies in the scene: the Mirage refuelling probe (SM_Mirage_RefuelProbe, per-polygon) and the
drogue parachute (SM_Drogue_Parachute, 24 convex hulls). They block each other and ignore everything else.
- every other level static-mesh component -> NoCollision; their mesh assets -> no collision geometry
  (simple-as-complex with no simple shapes), so nothing is cooked
- BP_RefuelHose components other than Parachute and BP_MiragePawn primitives -> NoCollision
Reports every primitive left with collision enabled."""
import unreal
eal = unreal.EditorAssetLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem); SDL = unreal.SubobjectDataBlueprintFunctionLibrary
log = lambda s: unreal.log("[ProbeChuteColl] " + s)
PROBE = "/Game/AirRefueler/Models/Aircraft/Mirage/SM_Mirage_RefuelProbe"
CR, CC = unreal.CollisionResponseType, unreal.CollisionChannel
def probe_profile(c):
    c.set_collision_profile_name("Custom")
    c.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
    c.set_collision_object_type(CC.ECC_WORLD_DYNAMIC)
    c.set_collision_response_to_all_channels(CR.ECR_IGNORE)
    c.set_collision_response_to_channel(CC.ECC_PHYSICS_BODY, CR.ECR_BLOCK)
def chute_profile(c):
    c.set_collision_profile_name("Custom")
    c.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
    c.set_collision_object_type(CC.ECC_PHYSICS_BODY)
    c.set_collision_response_to_all_channels(CR.ECR_IGNORE)
    c.set_collision_response_to_channel(CC.ECC_WORLD_DYNAMIC, CR.ECR_BLOCK)
# ---- level actors (skip Blueprint instances: their components come from the BP templates below)
off_meshes, n_off = set(), 0
for a in eas.get_all_level_actors():
    if isinstance(a.get_class(), unreal.BlueprintGeneratedClass): continue
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        sm = c.static_mesh
        if sm and sm.get_path_name().split(".")[0] == PROBE:
            c.modify(); probe_profile(c); log("probe component on %s" % a.get_actor_label()); continue
        if str(c.get_collision_profile_name()) != "NoCollision" or c.get_collision_enabled() != unreal.CollisionEnabled.NO_COLLISION:
            c.modify(); c.set_collision_profile_name("NoCollision"); n_off += 1
        if sm: off_meshes.add(sm.get_path_name().split(".")[0])
log("level components switched to NoCollision: %d" % n_off)
# ---- mesh assets: no collision geometry except the probe (complex) and the parachute (hulls)
n_geo = 0
for p in sorted(off_meshes):
    if p.endswith("SM_Drogue_Parachute"): continue
    sm = eal.load_asset(p); bs = sm.get_editor_property("body_setup")
    if not bs: continue
    has_simple = bs.get_editor_property("agg_geom").get_editor_property("convex_elems") or bs.get_editor_property("agg_geom").get_editor_property("box_elems") or bs.get_editor_property("agg_geom").get_editor_property("sphere_elems")
    if bs.get_editor_property("collision_trace_flag") != unreal.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX or has_simple:
        unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).remove_collisions(sm)
        bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX)
        eal.save_loaded_asset(sm, False); n_geo += 1
log("mesh assets stripped of collision geometry: %d" % n_geo)
psm = eal.load_asset(PROBE)
psm.get_editor_property("body_setup").set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
eal.save_loaded_asset(psm, False)
# ---- Blueprint templates
for bpp in ("/Game/AirRefueler/Sim/BP_RefuelHose", "/Game/AirRefueler/Sim/BP_MiragePawn"):
    bp = eal.load_asset(bpp)
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        o = SDL.get_object(SDL.get_data(h))
        if not isinstance(o, unreal.PrimitiveComponent): continue
        n = o.get_name().replace("_GEN_VARIABLE", "")
        if n == "Parachute":
            chute_profile(o)
        elif o.get_collision_enabled() != unreal.CollisionEnabled.NO_COLLISION:
            o.set_collision_profile_name("NoCollision"); log("%s.%s -> NoCollision" % (bpp.rsplit("/",1)[1], n))
    unreal.BlueprintEditorLibrary.compile_blueprint(bp); eal.save_loaded_asset(bp, False)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
# ---- report what still collides (level instances, after BP recompile)
left = []
for a in eas.get_all_level_actors():
    for c in a.get_components_by_class(unreal.PrimitiveComponent):
        if c.get_collision_enabled() != unreal.CollisionEnabled.NO_COLLISION:
            left.append("%s.%s(%s)" % (a.get_actor_label(), c.get_name(), str(c.get_collision_object_type()).split(".")[-1]))
log("primitives with collision now: %s" % left)
