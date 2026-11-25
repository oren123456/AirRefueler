"""Right-wing refuelling pod: mirror the left pod meshes (pod2: pCylinder11, NONE1, NONE11) across the tanker centre
plane (x -> -x) (*_R, attached to wings_grp), and spawn a second working hose (SimHose_RightPod, BP_RefuelHose)
at the mirrored hose exit. Re-runnable."""
import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
log = lambda *x: unreal.log("[PodRight] " + " ".join(str(v) for v in x))
acts = {a.get_actor_label(): a for a in eas.get_all_level_actors()}
for l in ("pod1R", "pCylinder11_R", "NONE1_R", "NONE11_R", "SimHose_RightPod"):
    if l in acts: eas.destroy_actor(acts[l])
acts = {a.get_actor_label(): a for a in eas.get_all_level_actors()}
wings = acts["wings_grp"]
for src in ("pCylinder11", "NONE1", "NONE11"):
    a = acts[src]
    t = a.get_actor_transform()
    q = t.rotation; s = t.scale3d; p = t.translation
    nq = unreal.Quat(q.x, -q.y, -q.z, q.w)                     # reflection across the YZ plane
    nt = unreal.Transform(unreal.Vector(-p.x, p.y, p.z), nq.rotator(), unreal.Vector(-s.x, s.y, s.z))
    d = eas.duplicate_actor(a, None, unreal.Vector(0, 0, 0))
    d.set_actor_label(src + "_R")
    d.detach_from_actor(unreal.DetachmentRule.KEEP_WORLD, unreal.DetachmentRule.KEEP_WORLD, unreal.DetachmentRule.KEEP_WORLD)
    d.set_actor_transform(nt, False, True)
    d.attach_to_actor(wings, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
    o, e = a.get_actor_bounds(False); o2, e2 = d.get_actor_bounds(False)
    log(src, "L ctr", [round(o.x), round(o.y), round(o.z)], "-> R ctr", [round(o2.x), round(o2.y), round(o2.z)])
left = acts["SimHose_LeftPod"]; lp = left.get_actor_location()
bp = unreal.EditorAssetLibrary.load_asset("/Game/AirRefueler/Sim/BP_RefuelHose")
h = eas.spawn_actor_from_object(bp, unreal.Vector(-lp.x, lp.y, lp.z), left.get_actor_rotation())
h.set_actor_label("SimHose_RightPod")
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
log("right hose at", h.get_actor_location(), "| left hose at", lp)
