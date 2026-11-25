"""Dump the front-cockpit meshes that use the Salon atlas: per triangle world positions + UVs, and the M_MayaPBR
texture parameter names -> Saved/ClaudeShots/cockpit_tris.json (for offline texture baking)."""
import unreal, json
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem); mel = unreal.MaterialEditingLibrary
EYE = unreal.Vector(-1727.25, -4609.5, 265.4)
out = {"meshes": {}}
for a in eas.get_all_level_actors():
    if not isinstance(a, unreal.StaticMeshActor): continue
    smc = a.static_mesh_component; m = smc.static_mesh
    if not m: continue
    mats = [smc.get_material(i).get_name() if smc.get_material(i) else "" for i in range(smc.get_num_materials())]
    if not any("Salon" in x for x in mats): continue
    o, e = a.get_actor_bounds(False)
    if (o - EYE).length() > 250: continue
    xf = smc.get_world_transform()
    v, t, n, uv, tg = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(m, 0, 0)
    wv = [xf.transform_location(p) for p in v]
    out["meshes"][a.get_actor_label()] = {"mesh": m.get_name(), "pos": [[round(p.x, 2), round(p.y, 2), round(p.z, 2)] for p in wv],
                                         "uv": [[round(q.x, 6), round(q.y, 6)] for q in uv], "tri": list(t)}
par = unreal.load_asset("/Game/AirRefueler/Materials/M_MayaPBR")
out["tex_params"] = [str(x) for x in mel.get_texture_parameter_names(par)]
out["scalar_params"] = [str(x) for x in mel.get_scalar_parameter_names(par)]
open(unreal.Paths.project_saved_dir() + "ClaudeShots/cockpit_tris.json", "w").write(json.dumps(out))
unreal.log("[CockpitExport] %s" % {k: len(v["tri"]) // 3 for k, v in out["meshes"].items()})
