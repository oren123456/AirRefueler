"""Remove pod1 (wrongly placed right pod: pod1 + pCylinder1, NONE1, Null, Hose_RightPod) and all CineCameraActors
(plus their now-empty group actor camaras_GRP)."""
import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
log = lambda *x: unreal.log("[RemovePod1] " + " ".join(str(v) for v in x))
acts = eas.get_all_level_actors()
def descendants(root):
    out = [root]
    for a in acts:
        p = a.get_attach_parent_actor()
        while p:
            if p == root:
                out.append(a); break
            p = p.get_attach_parent_actor()
    return out
kill = []
for a in acts:
    if a.get_actor_label() == "pod1":
        kill += descendants(a)
    if isinstance(a, unreal.CineCameraActor):
        kill.append(a)
grp = [a for a in acts if a.get_actor_label() == "camaras_GRP"]
for g in grp:
    rest = [c for c in descendants(g)[1:] if not isinstance(c, unreal.CineCameraActor)]
    if not rest:
        kill.append(g)
kill = list({a.get_name(): a for a in kill}.values())
log("deleting", sorted(a.get_actor_label() for a in kill))
for a in kill:
    eas.destroy_actor(a)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
log("done", len(kill))
