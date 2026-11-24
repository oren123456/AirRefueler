"""Mirage: per-polygon collision (Use Complex As Simple) on every Mirage mesh, so the drogue parachute hits the real shape.
The Mirage meshes are kinematic (moved by the pawn), which is allowed for complex collision. Removes the old Col_* capsules."""
import unreal
eal = unreal.EditorAssetLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
log = lambda *x: unreal.log("[MirageColl] " + " ".join(str(v) for v in x))
acts = eas.get_all_level_actors()
root = [a for a in acts if a.get_actor_label() == "Mirage_2000N"][0]
def is_under(a, r):
    p = a.get_attach_parent_actor()
    while p:
        if p == r: return True
        p = p.get_attach_parent_actor()
    return False
meshes, ncomp = set(), 0
for a in acts:
    if a == root or is_under(a, root):
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            if not c.static_mesh: continue
            c.modify()
            c.set_collision_profile_name("BlockAllDynamic")   # object type WorldDynamic -> the parachute blocks it
            ncomp += 1
            meshes.add(c.static_mesh.get_path_name())
for p in sorted(meshes):
    sm = eal.load_asset(p)
    bs = sm.get_editor_property("body_setup")
    bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    eal.save_loaded_asset(sm, False)
log("components", ncomp, "meshes", len(meshes))
# remove the capsule colliders from the pawn
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem); SDL = unreal.SubobjectDataBlueprintFunctionLibrary
pawn = eal.load_asset("/Game/AirRefueler/Sim/BP_MiragePawn")
hs = {}
for h in sds.k2_gather_subobject_data_for_blueprint(pawn):
    o = SDL.get_object(SDL.get_data(h))
    if o: hs[o.get_name().replace("_GEN_VARIABLE", "")] = h
caps = [hs[k] for k in hs if k.startswith("Col_")]
if caps:
    root_h = hs.get("DefaultSceneRoot")
    sds.delete_subobjects(root_h, caps, pawn)
unreal.BlueprintEditorLibrary.compile_blueprint(pawn); eal.save_loaded_asset(pawn)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
log("capsules removed", len(caps))
