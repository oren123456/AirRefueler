"""Islands of Mesh_ncl_365 (world space) + distance to the Mirage ProbeTip -> Saved/ClaudeShots/probe_islands.json"""
import unreal, json
G = unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
comp = None
for a in eas.get_all_level_actors():
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        sm = c.get_editor_property("static_mesh")
        if sm and sm.get_name() == "Mesh_ncl_365":
            comp, owner = c, a
pawn = next(a for a in eas.get_all_level_actors() if a.get_actor_label() == "SimPlayer_Mirage")
tip = [c for c in pawn.get_components_by_class(unreal.SceneComponent) if c.get_name() == "ProbeTip"][0].get_world_location()
sm = comp.get_editor_property("static_mesh")
xf = comp.get_world_transform()
dm = unreal.DynamicMesh()
dm, _ = G.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(sm, dm, unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
nt = G.GeometryScript_MeshQueries.get_num_triangle_i_ds(dm)
par = {}
def f(x):
    while par.setdefault(x, x) != x:
        par[x] = par[par[x]]; x = par[x]
    return x
tris = []
for t in range(nt):
    if not G.GeometryScript_MeshQueries.is_valid_triangle_id(dm, t): continue
    ix = G.GeometryScript_MeshQueries.get_triangle_indices(dm, t)
    ix = ix[0] if isinstance(ix, tuple) else ix
    a, b, c = ix.x, ix.y, ix.z
    par[f(b)] = f(a); par[f(c)] = f(a)
    r = G.GeometryScript_MeshQueries.get_triangle_positions(dm, t)
    vs = [xf.transform_location(v) for v in r if isinstance(v, unreal.Vector)]
    tris.append((t, a, vs))
isl = {}
for t, a, vs in tris:
    k = f(a)
    d = isl.setdefault(k, {"n": 0, "min": [1e9]*3, "max": [-1e9]*3, "tris": []})
    d["n"] += 1; d["tris"].append(t)
    for v in vs:
        for i, q in enumerate((v.x, v.y, v.z)):
            d["min"][i] = min(d["min"][i], q); d["max"][i] = max(d["max"][i], q)
out = []
for k, d in isl.items():
    c = [(d["min"][i] + d["max"][i]) / 2 for i in range(3)]
    dist = ((c[0]-tip.x)**2 + (c[1]-tip.y)**2 + (c[2]-tip.z)**2) ** 0.5
    out.append({"n": d["n"], "min": [round(x, 1) for x in d["min"]], "max": [round(x, 1) for x in d["max"]], "dist": round(dist, 1), "tris": d["tris"]})
out.sort(key=lambda d: d["dist"])
path = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()) + "ClaudeShots/probe_islands.json"
json.dump({"owner": owner.get_actor_label(), "comp": comp.get_name(), "mesh": sm.get_path_name(), "mats": [str(m.material_slot_name) for m in sm.static_materials],
           "tip": [tip.x, tip.y, tip.z], "xf": [xf.translation.x, xf.translation.y, xf.translation.z, xf.rotation.rotator().pitch, xf.rotation.rotator().yaw, xf.rotation.rotator().roll, xf.scale3d.x],
           "ntris": len(tris), "islands": out}, open(path, "w"))
unreal.log("[ProbeIsl] %s %s tris=%d islands=%d" % (owner.get_actor_label(), sm.get_path_name(), len(tris), len(out)))
