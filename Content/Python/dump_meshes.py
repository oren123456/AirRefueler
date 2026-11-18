"""Dump actors whose mesh uses any of the given material names -> Saved/ClaudeShots/dump.json"""
import unreal, sys, json
want = set(sys.argv[1:])
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
sme = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
out = []
for a in eas.get_all_level_actors():
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        mats = [m.get_name() if m else None for m in c.get_materials()]
        if (not want) or (want & set(mats)):
            p = a.get_attach_parent_actor()
            sm = c.static_mesh
            b = sm.get_bounding_box() if sm else None
            out.append({"label": a.get_actor_label(), "parent": p.get_actor_label() if p else None,
                        "mesh": sm.get_name() if sm else None, "mats": mats, "visible": c.is_visible(), "uvs": sme.get_num_uv_channels(sm, 0) if sm else 0,
                        "size": [round(b.max.x - b.min.x), round(b.max.y - b.min.y), round(b.max.z - b.min.z)] if b else None})
path = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()) + "ClaudeShots/dump.json"
open(path, "w").write(json.dumps(out, indent=0))
unreal.log("[Dump] %d components -> %s" % (len(out), path))
