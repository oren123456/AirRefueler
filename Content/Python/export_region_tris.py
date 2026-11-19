"""Export triangles of an actor's mesh whose world-space centroid is inside a box -> Saved/ClaudeShots/region_<label>.json
argv: label xmin xmax ymin ymax zmin zmax"""
import unreal, json, sys
label = sys.argv[1]
bx = [float(v) for v in sys.argv[2:8]]
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
a = next(x for x in eas.get_all_level_actors() if x.get_actor_label() == label)
c = a.get_component_by_class(unreal.StaticMeshComponent)
xf = c.get_world_transform()
md = c.static_mesh.get_static_mesh_description(0)
n = md.get_triangle_count()
out = []
for t in range(n):
    vis = md.get_triangle_vertex_instances(unreal.TriangleID(t))
    pts = []
    for vi in vis:
        p = md.get_vertex_position(md.get_vertex_instance_vertex(vi))
        w = xf.transform_location(p)
        uv = md.get_vertex_instance_uv(vi, 0)
        pts.append([round(w.x, 1), round(w.y, 1), round(w.z, 1), round(uv.x, 5), round(uv.y, 5)])
    cx = sum(p[0] for p in pts) / 3; cy = sum(p[1] for p in pts) / 3; cz = sum(p[2] for p in pts) / 3
    if bx[0] <= cx <= bx[1] and bx[2] <= cy <= bx[3] and bx[4] <= cz <= bx[5]:
        out.append([t, pts])
path = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()) + "ClaudeShots/region_%s.json" % label
json.dump({"label": label, "mesh": c.static_mesh.get_path_name(), "total": n, "tris": out}, open(path, "w"))
unreal.log("[Region] %s: %d of %d triangles in box" % (label, len(out), n))
