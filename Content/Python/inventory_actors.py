"""Inventory: group level actors by top-level root; flag visible meshes, hidden, cameras, sequence bindings."""
import unreal, json
SEQ = "/Game/AirRefueler/Scene/RootNode_TrackSetNode"
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = eas.get_all_level_actors()
seq = unreal.load_asset(SEQ)
bound = set()
for b in seq.get_bindings():
    if b.get_tracks():
        bound.add(str(b.get_display_name()))
kids = {}
for a in actors:
    p = a.get_attach_parent_actor()
    if p:
        kids.setdefault(p.get_path_name(), []).append(a)
def desc(a):
    out = [a]
    for k in kids.get(a.get_path_name(), []):
        out += desc(k)
    return out
roots = [a for a in actors if not a.get_attach_parent_actor()]
if any(a.get_actor_label() == "RootNode" for a in roots):
    rn = next(a for a in roots if a.get_actor_label() == "RootNode")
    roots = [a for a in roots if a is not rn] + kids.get(rn.get_path_name(), [])
rows = []
for r in roots:
    d = desc(r)
    vis_mesh = hid_mesh = 0
    cams = 0
    for a in d:
        for c in a.get_components_by_class(unreal.PrimitiveComponent):
            if isinstance(c, (unreal.StaticMeshComponent, unreal.SkeletalMeshComponent)):
                if c.is_visible(): vis_mesh += 1
                else: hid_mesh += 1
        if isinstance(a, unreal.CameraActor): cams += 1
    rows.append({"root": r.get_actor_label(), "class": r.get_class().get_name(), "actors": len(d),
                 "visible_meshes": vis_mesh, "hidden_meshes": hid_mesh, "cameras": cams,
                 "animated": sum(1 for a in d if a.get_actor_label() in bound),
                 "folder": str(r.get_folder_path()), "tags": [str(t) for t in r.tags]})
path = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()) + "ClaudeShots/inventory.json"
open(path, "w").write(json.dumps(rows, indent=0))
unreal.log("[Inventory] %d roots, %d actors -> %s" % (len(rows), len(actors), path))
