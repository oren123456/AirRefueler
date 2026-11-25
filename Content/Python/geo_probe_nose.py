import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
acts = eas.get_all_level_actors()
log = lambda s: unreal.log("[Geo] " + s)
pawn = next(a for a in acts if a.get_actor_label() == "SimPlayer_Mirage")
root = next(a for a in acts if a.get_actor_label() == "Mirage_2000N")
hose = next(a for a in acts if a.get_actor_label() == "SimHose_LeftPod")
tip = [c for c in pawn.get_components_by_class(unreal.SceneComponent) if c.get_name() == "ProbeTip"][0].get_world_location()
P = pawn.get_actor_location()
log("pawn %s rot %s tip %s tip-pawn %s" % (P, pawn.get_actor_rotation(), tip, tip - P))
best = None
for a in acts:
    q = a
    while q is not None and q != root: q = q.get_attach_parent_actor()
    if q is None or not isinstance(a, unreal.StaticMeshActor) or a.get_actor_label() == "RefuelProbe": continue
    o, e = a.get_actor_bounds(False)
    if e.length() > 2000: continue
    if best is None or o.y + e.y > best[0]: best = (o.y + e.y, a.get_actor_label(), o, e)
log("frontmost mesh %s maxY=%.1f center=%s ext=%s  -> nose-pawn %s" % (best[1], best[0], best[2], best[3], unreal.Vector(best[2].x, best[0], best[2].z) - P))
H = hose.get_actor_location()
log("hose actor %s rot %s" % (H, hose.get_actor_rotation()))
near = []
for a in acts:
    if isinstance(a, unreal.StaticMeshActor):
        o, e = a.get_actor_bounds(False)
        if abs(o.x - H.x) < 200 and abs(o.z - H.z) < 200 and abs(o.y - H.y) < 600 and e.length() < 800:
            near.append((a.get_actor_label(), o, e))
for n, o, e in near[:8]: log("near pod: %s center=%s ext=%s" % (n, o, e))
