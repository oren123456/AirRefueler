"""Collect all triangles (every section, every mesh actor) in front of the khaki HUD-control box face -> Saved/ClaudeShots/ufcp_tris.json"""
import unreal, json
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
EYE = unreal.Vector(-1727.25, -4609.5, 265.4)
lo, hi = (-1738.0, -4570.0, 236.0), (-1716.0, -4552.0, 260.0)
out = []
for a in eas.get_all_level_actors():
    for smc in a.get_components_by_class(unreal.StaticMeshComponent):
        m = smc.static_mesh
        if not m: continue
        o, e = a.get_actor_bounds(False)
        if any(o.x - e.x > hi[0] or o.x + e.x < lo[0] or False for _ in [0]) or o.y - e.y > hi[1] or o.y + e.y < lo[1] or o.z - e.z > hi[2] or o.z + e.z < lo[2]: continue
        if e.length() > 5000: unreal.log("[UfcpProbe] big " + a.get_actor_label())
        xf = smc.get_world_transform()
        for s in range(m.get_num_sections(0)):
            v, t, n, uv, tg = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(m, 0, s)
            wv = [xf.transform_location(p) for p in v]
            mat = smc.get_material(s); mn = mat.get_name() if mat else ""
            for i in range(0, len(t), 3):
                P = [wv[t[i]], wv[t[i + 1]], wv[t[i + 2]]]
                c = [(P[0].x + P[1].x + P[2].x) / 3, (P[0].y + P[1].y + P[2].y) / 3, (P[0].z + P[1].z + P[2].z) / 3]
                if all(lo[k] < c[k] < hi[k] for k in range(3)):
                    out.append({"a": a.get_actor_label(), "s": s, "m": mn, "p": [[round(q.x, 2), round(q.y, 2), round(q.z, 2)] for q in P],
                                "uv": [[round(uv[t[i + k]].x, 5), round(uv[t[i + k]].y, 5)] for k in range(3)]})
open(unreal.Paths.project_saved_dir() + "ClaudeShots/ufcp_tris.json", "w").write(json.dumps(out))
from collections import Counter
unreal.log("[UfcpProbe] %d tris %s" % (len(out), Counter((x["a"], x["s"], x["m"]) for x in out)))
