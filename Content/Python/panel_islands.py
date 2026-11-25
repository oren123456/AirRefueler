"""Locate atlas instrument islands (Content/Python/panel_islands_atlas.json, pixel boxes in T_Salon_Diffuse 8192) on the cockpit
meshes: world centre, normal, and the UV directions of face-right / face-up. -> panel_islands.json"""
import unreal, json
S = 8192.0
isl = json.load(open(unreal.Paths.project_dir() + "Content/Python/panel_islands_atlas.json"))   # islands found in T_Salon_Diffuse (purple outlines)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
EYE = unreal.Vector(-1727.25, -4609.5, 265.4)
tris = []
for a in eas.get_all_level_actors():
    if not isinstance(a, unreal.StaticMeshActor): continue
    smc = a.static_mesh_component; m = smc.static_mesh
    if not m or (a.get_actor_bounds(False)[0] - EYE).length() > 400: continue
    mats = [smc.get_material(i).get_name() if smc.get_material(i) else "" for i in range(smc.get_num_materials())]
    if not any("Salon" in x for x in mats): continue
    xf = smc.get_world_transform()
    v, t, n, uv, tg = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(m, 0, 0)
    wv = [xf.transform_location(p) for p in v]
    for i in range(0, len(t), 3):
        tris.append((a.get_actor_label(), [wv[t[i]], wv[t[i+1]], wv[t[i+2]]], [uv[t[i]], uv[t[i+1]], uv[t[i+2]]]))
out = []
for k, (x, y, w, h) in enumerate(isl):
    cu, cv = (x + w / 2.0) / S, (y + h / 2.0) / S
    hits = []
    for name, P, Q in tris:
        a, b, c = Q
        d = (b.x - a.x) * (c.y - a.y) - (c.x - a.x) * (b.y - a.y)
        if abs(d) < 1e-12: continue
        l1 = ((cu - a.x) * (c.y - a.y) - (c.x - a.x) * (cv - a.y)) / d
        l2 = ((b.x - a.x) * (cv - a.y) - (cu - a.x) * (b.y - a.y)) / d
        if l1 < -1e-4 or l2 < -1e-4 or l1 + l2 > 1 + 1e-4: continue
        p = P[0] + (P[1] - P[0]) * l1 + (P[2] - P[0]) * l2
        # world vectors of +u and +v: solve dP = Ju du + Jv dv from the two edges
        e1, e2 = P[1] - P[0], P[2] - P[0]; du1, dv1, du2, dv2 = b.x - a.x, b.y - a.y, c.x - a.x, c.y - a.y
        Ju = (e1 * dv2 - e2 * dv1) * (1.0 / d); Jv = (e2 * du1 - e1 * du2) * (1.0 / d)
        nrm = e1.cross(e2).normal()
        if nrm.dot(EYE - p) < 0: nrm = nrm * -1
        hits.append({"actor": name, "p": [round(p.x, 2), round(p.y, 2), round(p.z, 2)], "n": [round(nrm.x, 3), round(nrm.y, 3), round(nrm.z, 3)],
                     "Ju": [round(Ju.x, 1), round(Ju.y, 1), round(Ju.z, 1)], "Jv": [round(Jv.x, 1), round(Jv.y, 1), round(Jv.z, 1)],
                     "dist": round((p - EYE).length(), 1)})
    out.append({"i": k, "uv": [round(cu, 5), round(cv, 5)], "size": [round(w / S, 5), round(h / S, 5)], "hits": hits})
open(unreal.Paths.project_saved_dir() + "ClaudeShots/panel_islands.json", "w").write(json.dumps(out, indent=1))
unreal.log("[Islands] done %d tris" % len(tris))
