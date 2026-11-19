"""For each roundel UV point in Saved/ClaudeShots/roundel_query.json find the mesh triangles (in level actors
using that base-color texture) that contain it, and export world position, normal and the world directions of +u/+v.
-> Saved/ClaudeShots/roundel_world.json"""
import unreal, json
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()) + "ClaudeShots/"
Q = json.load(open(SAVED + "roundel_query.json"))
norm = lambda s: s.replace("-", "_").replace(" ", "_").lower()
want = {norm(k): k for k in Q}
mel = unreal.MaterialEditingLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

def stem_of(mat):
    if not isinstance(mat, unreal.MaterialInstance):
        return None
    t = mel.get_material_instance_texture_parameter_value(mat, "BaseColorTex")
    if not t: return None
    k = norm(t.get_name()).removeprefix("t_").removesuffix("_il")
    return want.get(k)

def bary(p, a, b, c):
    v0 = (b[0]-a[0], b[1]-a[1]); v1 = (c[0]-a[0], c[1]-a[1]); v2 = (p[0]-a[0], p[1]-a[1])
    den = v0[0]*v1[1] - v1[0]*v0[1]
    if abs(den) < 1e-14: return None
    l1 = (v2[0]*v1[1] - v1[0]*v2[1]) / den; l2 = (v0[0]*v2[1] - v2[0]*v0[1]) / den
    return (1-l1-l2, l1, l2)

out = []; seen = set()
for act in eas.get_all_level_actors():
    for comp in act.get_components_by_class(unreal.StaticMeshComponent):
        sm = comp.static_mesh
        if not sm: continue
        mats = comp.get_materials()
        slots = {i: stem_of(m) for i, m in enumerate(mats)}
        slots = {i: s for i, s in slots.items() if s}
        if not slots: continue
        xf = comp.get_world_transform()
        md = sm.get_static_mesh_description(0)
        for tid in range(md.get_triangle_count()):
            T = unreal.TriangleID(tid)
            pg = md.get_triangle_polygon_group(T).id_value if hasattr(md.get_triangle_polygon_group(T), "id_value") else None
            st = slots.get(pg) if pg is not None else None
            if st is None:
                if len(set(slots.values())) == 1 and pg is None: st = list(slots.values())[0]
                else: continue
            vis = md.get_triangle_vertex_instances(T)
            uvs = [md.get_vertex_instance_uv(vi, 0) for vi in vis]
            uvs = [(u.x, u.y) for u in uvs]
            for qi, (u, v, cx, cy) in enumerate(Q[st]):
                if min(x[0] for x in uvs) > u or max(x[0] for x in uvs) < u or min(x[1] for x in uvs) > v or max(x[1] for x in uvs) < v:
                    continue
                b = bary((u, v), *uvs)
                if not b or min(b) < -1e-4: continue
                P = [xf.transform_location(md.get_vertex_position(md.get_vertex_instance_vertex(vi))) for vi in vis]
                P = [(p.x, p.y, p.z) for p in P]
                # world gradient: solve dP = J * dUV for the triangle
                du1, dv1 = uvs[1][0]-uvs[0][0], uvs[1][1]-uvs[0][1]; du2, dv2 = uvs[2][0]-uvs[0][0], uvs[2][1]-uvs[0][1]
                e1 = [P[1][k]-P[0][k] for k in range(3)]; e2 = [P[2][k]-P[0][k] for k in range(3)]
                det = du1*dv2 - du2*dv1
                if abs(det) < 1e-14: continue
                dPdu = [(e1[k]*dv2 - e2[k]*dv1)/det for k in range(3)]; dPdv = [(e2[k]*du1 - e1[k]*du2)/det for k in range(3)]
                n = [e1[1]*e2[2]-e1[2]*e2[1], e1[2]*e2[0]-e1[0]*e2[2], e1[0]*e2[1]-e1[1]*e2[0]]
                pos = [sum(b[i]*P[i][k] for i in range(3)) for k in range(3)]
                key = (st, qi, act.get_actor_label())
                if key in seen: continue
                seen.add(key)
                out.append({"stem": st, "idx": qi, "key": "%d,%d" % (round(cx), round(cy)), "actor": act.get_actor_label(),
                            "pos": pos, "n": n, "dPdu": dPdu, "dPdv": dPdv, "fwd": [act.get_actor_forward_vector().x, act.get_actor_forward_vector().y, act.get_actor_forward_vector().z]})
json.dump(out, open(SAVED + "roundel_world.json", "w"), indent=1)
unreal.log("[Roundel] hits %d" % len(out))
