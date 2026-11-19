import unreal, json, math
sm = unreal.EditorAssetLibrary.load_asset("/Game/AirRefueler/Scene/Mesh_ncl_44")
md = sm.get_static_mesh_description(0)
pts = [md.get_vertex_position(unreal.VertexID(i)) for i in range(md.get_vertex_count())]
cx = sum(p.x for p in pts)/len(pts); cy = sum(p.y for p in pts)/len(pts)
zs = [p.z for p in pts]; z0, z1 = min(zs), max(zs)
prof = []
for k in range(10):
    a = z0 + (z1-z0)*k/10; b = z0 + (z1-z0)*(k+1)/10
    r = [math.hypot(p.x-cx, p.y-cy) for p in pts if a <= p.z <= b]
    prof.append([round(a,1), round(max(r),1) if r else None, len(r)])
json.dump({"c":[cx,cy], "z":[z0,z1], "prof":prof}, open(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()) + "ClaudeShots/drogue_prof.json","w"))
unreal.log("[DrogueProf] done")
