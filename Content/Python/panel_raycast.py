"""Ray-cast pixels of a pilot-eye capture (eye, pitch -30, yaw 90, hFOV 90, 1818x1255) against the cockpit meshes
(no collision on them) -> hit point, face normal, UV per instrument. Output Saved/ClaudeShots/panel_raycast.json"""
import unreal, math, json
EYE = unreal.Vector(-1727.25, -4609.5, 265.4); PITCH = -30.0; W, H = 1818.0, 1255.0
PTS = {"asi": (675, 720), "adi": (752, 707), "hsi": (735, 630), "alt": (1085, 705), "fuelctr": (905, 928),
       "mfd": (905, 735), "eng": (1310, 1075), "dig249": (595, 655), "r1": (1200, 595), "r2": (1200, 632)}
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
acts = [a for a in eas.get_all_level_actors() if isinstance(a, unreal.StaticMeshActor)
        if (a.get_actor_location() - EYE).length() < 400 or a.get_actor_label() in ("Devices", "Cockpit_Panel", "Cockpit", "Control_Device", "Devices2", "Devices3")]
tris = []
for a in acts:
    smc = a.static_mesh_component; m = smc.static_mesh
    if not m: continue
    o, e = a.get_actor_bounds(False)
    if (o - EYE).length() > 300: continue
    xf = smc.get_world_transform()
    for sec in range(m.get_num_sections(0)):
        v, t, n, uv, tg = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(m, 0, sec)
        wv = [xf.transform_location(p) for p in v]
        for i in range(0, len(t), 3):
            tris.append((a.get_actor_label(), wv[t[i]], wv[t[i+1]], wv[t[i+2]], uv[t[i]], uv[t[i+1]], uv[t[i+2]]))
cp, sp = math.cos(math.radians(PITCH)), math.sin(math.radians(PITCH))
F = unreal.Vector(0, cp, sp); R = unreal.Vector(-1, 0, 0); U = unreal.Vector(0, -sp, cp)
def ray(px, py):
    return (F + R * ((2 * px / W - 1)) + U * ((1 - 2 * py / H) * H / W)).normal()
def hit(d):
    best = None
    for name, a, b, c, ua, ub, uc in tris:
        e1 = b - a; e2 = c - a; pv = d.cross(e2); det = e1.dot(pv)
        if abs(det) < 1e-9: continue
        inv = 1.0 / det; tv = EYE - a; u = tv.dot(pv) * inv
        if u < 0 or u > 1: continue
        qv = tv.cross(e1); v = d.dot(qv) * inv
        if v < 0 or u + v > 1: continue
        tt = e2.dot(qv) * inv
        if tt > 1 and (best is None or tt < best[0]):
            nrm = e1.cross(e2).normal()
            if nrm.dot(d) > 0: nrm = nrm * -1
            uvp = ua * (1 - u - v) + ub * u + uc * v
            best = (tt, name, EYE + d * tt, nrm, uvp)
    return best
out = {"ntris": len(tris), "actors": [a.get_actor_label() for a in acts]}
for k, (x, y) in PTS.items():
    r = []
    for dx, dy in ((0, 0), (15, 0), (0, 15)):
        h = hit(ray(x + dx, y + dy))
        r.append(None if h is None else {"actor": h[1], "p": [round(h[2].x, 2), round(h[2].y, 2), round(h[2].z, 2)],
                 "n": [round(h[3].x, 3), round(h[3].y, 3), round(h[3].z, 3)], "uv": [round(h[4].x, 4), round(h[4].y, 4)], "dist": round(h[0], 1)})
    out[k] = r
open(unreal.Paths.project_saved_dir() + "ClaudeShots/panel_raycast.json", "w").write(json.dumps(out, indent=1))
unreal.log("[Raycast] done %d tris" % len(tris))
