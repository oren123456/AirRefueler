"""Only SM_Drogue_Parachute keeps a collision model (its simple convex hull, used as complex too).
All other static meshes under /Game/AirRefueler lose their simple collision and use 'simple as complex'
(= no collision geometry at all); all level static-mesh components get the NoCollision preset."""
import unreal
eal = unreal.EditorAssetLibrary
ses = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
log = lambda *x: unreal.log("[CollOnlyChute] " + " ".join(str(v) for v in x))
KEEP = "/Game/AirRefueler/Sim/SM_Drogue_Parachute"
SAC = unreal.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX
n_assets = n_changed = 0
for p in eal.list_assets("/Game/AirRefueler", recursive=True, include_folder=False):
    ad = eal.find_asset_data(p)
    if str(ad.asset_class_path.asset_name) != "StaticMesh":
        continue
    n_assets += 1
    sm = eal.load_asset(p)
    bs = sm.get_editor_property("body_setup")
    changed = False
    if p.split(".")[0] == KEEP:
        if bs and bs.get_editor_property("collision_trace_flag") != SAC:
            bs.set_editor_property("collision_trace_flag", SAC); changed = True
        log("parachute simple shapes:", ses.get_convex_collision_count(sm), "trace flag ->", bs.get_editor_property("collision_trace_flag"))
    else:
        if ses.get_simple_collision_count(sm) > 0 or ses.get_convex_collision_count(sm) > 0:
            ses.remove_collisions(sm); changed = True
        bs = sm.get_editor_property("body_setup")
        if bs and bs.get_editor_property("collision_trace_flag") != SAC:
            bs.set_editor_property("collision_trace_flag", SAC); changed = True
    if changed:
        eal.save_loaded_asset(sm, False); n_changed += 1
log("static meshes", n_assets, "changed", n_changed)

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
n_comp = 0
for a in eas.get_all_level_actors():
    if a.get_class().get_name().startswith("BP_RefuelHose"):
        continue      # its Parachute keeps collision
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        if str(c.get_collision_profile_name()) != "NoCollision":
            c.modify(); c.set_collision_profile_name("NoCollision"); n_comp += 1
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
log("level components set to NoCollision:", n_comp)
