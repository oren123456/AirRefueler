"""Split the drogue mesh (Mesh_ncl_44) into SM_Drogue_Body and SM_Drogue_Parachute (canopy ribs + ring).
Both are re-based: hub (hose coupling) at the origin, drogue axis +X toward the hose, basket toward -X (rim at x=-83).
The parachute gets one convex-hull simple collision (editable in its Static Mesh editor). The body has no collision."""
import unreal
G = unreal
SRC = "/Game/AirRefueler/Scene/Mesh_ncl_44"
DST = "/Game/AirRefueler/Sim"
SPLIT_X = -45.0          # neck between body and canopy (cm along drogue axis)
eal = unreal.EditorAssetLibrary
log = lambda *x: unreal.log("[SplitDrogue] " + " ".join(str(v) for v in x))
src = eal.load_asset(SRC)
mat = src.static_materials[0].material_interface

def make(name, keep_parachute):
    dm = unreal.DynamicMesh()
    dm, _ = G.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(src, dm, unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
    xf = unreal.Transform(location=unreal.Vector(4848.0, -207.8, -0.8), rotation=unreal.Rotator(roll=0.0, pitch=-90.0, yaw=0.0), scale=unreal.Vector(1, 1, 1))
    dm = G.GeometryScript_MeshTransforms.transform_mesh(dm, xf)
    drop = []
    for tid in range(G.GeometryScript_MeshQueries.get_num_triangle_i_ds(dm)):
        if not G.GeometryScript_MeshQueries.is_valid_triangle_id(dm, tid):
            continue
        r = G.GeometryScript_MeshQueries.get_triangle_positions(dm, tid)
        vs = [v for v in r if isinstance(v, unreal.Vector)]
        cx = sum(v.x for v in vs) / len(vs)
        is_chute = cx < SPLIT_X
        if is_chute != keep_parachute:
            drop.append(tid)
    G.GeometryScript_MeshEdits.delete_triangles_from_mesh(dm, G.GeometryScript_List.convert_array_to_index_list(drop, unreal.GeometryScriptIndexType.TRIANGLE), False)
    path = DST + "/" + name
    if eal.does_asset_exist(path):
        eal.delete_asset(path)
    opts = unreal.GeometryScriptCreateNewStaticMeshAssetOptions()
    opts.set_editor_property("enable_nanite", False)
    opts.set_editor_property("enable_collision", False)
    sm, _ = G.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dm, path, opts)
    for i in range(len(sm.static_materials)):
        sm.set_material(i, mat)
    b = sm.get_bounding_box()
    log(name, "tris", G.GeometryScript_MeshQueries.get_num_triangle_i_ds(dm) - len(drop), "bounds", b.min, b.max)
    return sm

body = make("SM_Drogue_Body", False)
chute = make("SM_Drogue_Parachute", True)
ses = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
ok = ses.set_convex_decomposition_collisions(chute, 1, 32, 100000)
log("parachute convex collision:", ok)
bs = chute.get_editor_property("body_setup")
try:
    bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_DEFAULT)
except Exception as e:
    log("trace flag", e)
for sm in (body, chute):
    eal.save_loaded_asset(sm)
log("done")
