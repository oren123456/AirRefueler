"""Export triangles (local positions + UV0) of the mesh used by given actor labels -> Saved/ClaudeShots/tris_<label>.json"""
import unreal, json, sys
labels = sys.argv[1:] or ["WindShield"]
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
out_dir = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()) + "ClaudeShots/"
for a in eas.get_all_level_actors():
    if a.get_actor_label() not in labels:
        continue
    c = a.get_component_by_class(unreal.StaticMeshComponent)
    sm = c.static_mesh
    md = sm.get_static_mesh_description(0)
    n = md.get_triangle_count()
    tris = []
    for t in range(n):
        vis = md.get_triangle_vertex_instances(unreal.TriangleID(t))
        tri = []
        for vi in vis:
            v = md.get_vertex_instance_vertex(vi)
            p = md.get_vertex_position(v)
            uv = md.get_vertex_instance_uv(vi, 0)
            tri.append([round(p.x, 2), round(p.y, 2), round(p.z, 2), round(uv.x, 5), round(uv.y, 5)])
        tris.append(tri)
    xf = a.get_actor_transform()
    json.dump({"label": a.get_actor_label(), "mesh": sm.get_path_name(), "tris": tris,
               "loc": [xf.translation.x, xf.translation.y, xf.translation.z],
               "rot": [xf.rotation.rotator().pitch, xf.rotation.rotator().yaw, xf.rotation.rotator().roll]},
              open(out_dir + "tris_" + a.get_actor_label() + ".json", "w"))
    unreal.log("[Tris] %s: %d triangles" % (a.get_actor_label(), n))
