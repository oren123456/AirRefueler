"""Remove the Su-30 (keep the Mirage = player aircraft). argv[1] == 'go' deletes, otherwise dry run.
Su-30 = descendants of Suchoi_Ctrl + any actor whose bounds lie in the Su-30 box, + their descendants."""
import unreal, sys, json
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
acts = eas.get_all_level_actors()
BOX = ((-800, 500), (-8700, -6700), (-700, -100))
def desc(root):
    out = []
    for a in acts:
        p = a.get_attach_parent_actor()
        while p:
            if p == root: out.append(a); break
            p = p.get_attach_parent_actor()
    return out
keep_roots = [a for a in acts if a.get_actor_label() in ("SimPlayer_Mirage", "Mirage_2000N")]
keep = set(x.get_name() for r in keep_roots for x in [r] + desc(r))
kill = {}
for a in acts:
    if a.get_actor_label() in ("Suchoi_Ctrl",):
        for x in [a] + desc(a): kill[x.get_name()] = x
    o, e = a.get_actor_bounds(False)
    if e.x > 0 or e.y > 0 or e.z > 0:
        lo = (o.x - e.x, o.y - e.y, o.z - e.z); hi = (o.x + e.x, o.y + e.y, o.z + e.z)
        if all(BOX[i][0] <= lo[i] and hi[i] <= BOX[i][1] for i in range(3)):
            for x in [a] + desc(a): kill[x.get_name()] = x
for k in list(kill):
    if k in keep: kill.pop(k)
# parents that would be left empty (e.g. Sliders_24 that only holds Body1)
for a in acts:
    if a.get_name() in kill or a.get_name() in keep: continue
    d = desc(a)
    if d and all(x.get_name() in kill for x in d) and a.get_actor_label() not in ("RootNode",):
        kill[a.get_name()] = a
labels = sorted(a.get_actor_label() for a in kill.values())
unreal.log("[RemoveSu30] %d actors: %s" % (len(labels), ", ".join(labels[:400])))
if len(sys.argv) > 1 and sys.argv[1] == "go":
    for a in kill.values():
        eas.destroy_actor(a)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    unreal.log("[RemoveSu30] deleted %d" % len(labels))
