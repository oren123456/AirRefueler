"""Export sampled UVs of meshes that use the hull materials with refraction masks -> Saved/ClaudeShots/uvs.json"""
import unreal, json
HULL = {"MI_Su_30_Body_VRay": "Su-30_Body_Refraction", "MI_mat_Housing_VRay1": "Housing_Refraction",
        "MI_Salon_VRay1": "Salon_Refraction", "MI_Glass_Su30": "Su-30_Body_Refraction", "MI_Glass_Mirage": "Housing_Refraction"}
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
out = {}
for a in eas.get_all_level_actors():
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        sm = c.static_mesh
        if not sm or not c.is_visible():
            continue
        mats = [m.get_name() if m else "" for m in c.get_materials()]
        hit = [HULL[m] for m in mats if m in HULL]
        if not hit:
            continue
        key = sm.get_path_name()
        e = out.setdefault(key, {"actors": [], "mask": hit[0], "mats": mats, "uvs": []})
        e["actors"].append(a.get_actor_label())
        if e["uvs"]:
            continue
        md = sm.get_static_mesh_description(0)
        n = md.get_vertex_instance_count()
        step = max(1, n // 4000)
        uvs = []
        for i in range(0, n, step):
            uv = md.get_vertex_instance_uv(unreal.VertexInstanceID(i), 0)
            uvs.append([round(uv.x, 4), round(uv.y, 4)])
        e["uvs"] = uvs
        e["n"] = n
path = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()) + "ClaudeShots/uvs.json"
open(path, "w").write(json.dumps(out))
unreal.log("[UV] %d meshes -> %s" % (len(out), path))
