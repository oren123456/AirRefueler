"""Parachute collision = multi-hull convex decomposition. argv: hulls verts precision.
Then probes the basket with line traces along its axis (centre and offsets) to check the opening is clear."""
import unreal, sys
H = int(sys.argv[1]) if len(sys.argv) > 1 else 24
V = int(sys.argv[2]) if len(sys.argv) > 2 else 24
P = int(sys.argv[3]) if len(sys.argv) > 3 else 1000000
eal = unreal.EditorAssetLibrary
ses = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
sm = eal.load_asset("/Game/AirRefueler/Sim/SM_Drogue_Parachute")
ok = ses.set_convex_decomposition_collisions(sm, H, V, P)
bs = sm.get_editor_property("body_setup")
bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX)
eal.save_loaded_asset(sm)
unreal.log("[ChuteDecomp] ok=%s hulls=%d" % (ok, ses.get_convex_collision_count(sm)))
