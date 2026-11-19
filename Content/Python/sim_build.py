"""Refuel simulator: create BP_MiragePawn, BP_RefuelHose, BP_RefuelGameMode (+components) and place them in L_RefuelScene.
Graph logic is written separately (BlueprintTools.write_graph_dsl). Re-runnable: existing BPs are kept, components re-checked."""
import unreal
SIM = "/Game/AirRefueler/Sim"
eal = unreal.EditorAssetLibrary
at = unreal.AssetToolsHelpers.get_asset_tools()
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
SDL = unreal.SubobjectDataBlueprintFunctionLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
log = lambda *x: unreal.log("[SimBuild] " + " ".join(str(v) for v in x))

MIRAGE_ROOT = unreal.Vector(1682.6, -9933.1, -224.0)
PROBE_TIP = unreal.Vector(1633.0, -9384.0, -229.0)
EYE = unreal.Vector(1683.5, -9640.0, -200.0)
POD_EXIT = unreal.Vector(1657.6, -299.1, 333.1)

def make_bp(name, parent):
    path = SIM + "/" + name
    if eal.does_asset_exist(path):
        return eal.load_asset(path)
    f = unreal.BlueprintFactory(); f.set_editor_property("parent_class", parent)
    return at.create_asset(name, SIM, None, f)

def comps(bp):
    out = {}
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        d = SDL.get_data(h); o = SDL.get_object(d)
        if o: out[o.get_name().replace("_GEN_VARIABLE", "")] = (h, o)
    return out

def add(bp, parent_name, cls, name):
    c = comps(bp)
    if name in c:
        return c[name][1]
    ph = c[parent_name][0]
    h, fail = sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=ph, new_class=cls, blueprint_context=bp))
    sds.rename_subobject(h, unreal.Text(name))
    return SDL.get_object(SDL.get_data(h))

def root_name(bp):
    for k, (h, o) in comps(bp).items():
        if isinstance(o, unreal.SceneComponent):
            return k
# ---------- pawn
pawn = make_bp("BP_MiragePawn", unreal.Pawn)
add(pawn, list(comps(pawn).keys())[0], unreal.SceneComponent, "Root") if root_name(pawn) is None else None
r = root_name(pawn)
cam = add(pawn, r, unreal.CameraComponent, "PilotCam")
cam.set_editor_property("relative_location", EYE - MIRAGE_ROOT)
cam.set_editor_property("relative_rotation", unreal.Rotator(0, 0, 90))   # roll,pitch,yaw order in py ctor? set explicitly below
rot = unreal.Rotator(); rot.yaw = 90.0; rot.pitch = 0.0; rot.roll = 0.0
cam.set_editor_property("relative_rotation", rot)
cam.set_editor_property("field_of_view", 90.0)
probe = add(pawn, r, unreal.SceneComponent, "ProbeTip")
probe.set_editor_property("relative_location", PROBE_TIP - MIRAGE_ROOT)
cdo = unreal.get_default_object(pawn.generated_class())
unreal.BlueprintEditorLibrary.compile_blueprint(pawn)
# ---------- hose
hose = make_bp("BP_RefuelHose", unreal.Actor)
if root_name(hose) is None:
    add(hose, list(comps(hose).keys())[0], unreal.SceneComponent, "PodExit")
r = root_name(hose)
drogue = add(hose, r, unreal.SceneComponent, "Drogue")
dm = add(hose, "Drogue", unreal.StaticMeshComponent, "DrogueMesh")
dm.set_editor_property("static_mesh", eal.load_asset("/Game/AirRefueler/Scene/Mesh_ncl_44"))
rr = unreal.Rotator(); rr.pitch = -90.0
dm.set_editor_property("relative_rotation", rr)
dm.set_editor_property("relative_location", unreal.Vector(4848.0, -207.8, -0.8))   # hub of the drogue at Drogue origin, basket toward -X
dm.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION) if hasattr(dm, "set_collision_enabled") else None
cable = add(hose, r, unreal.CableComponent, "Hose")
for k, v in dict(cable_length=50.0, num_segments=24, solver_iterations=8, cable_width=7.0, num_sides=8,
                 cable_gravity_scale=1.0, end_location=unreal.Vector(0, 0, 0), substep_time=0.01).items():
    try: cable.set_editor_property(k, v)
    except Exception as e: log("cable prop", k, e)
unreal.BlueprintEditorLibrary.compile_blueprint(hose)
# ---------- game mode
gm = make_bp("BP_RefuelGameMode", unreal.GameModeBase)
unreal.BlueprintEditorLibrary.compile_blueprint(gm)
gcdo = unreal.get_default_object(gm.generated_class())
gcdo.set_editor_property("default_pawn_class", None)
for a in (pawn, hose, gm):
    eal.save_loaded_asset(a)
log("assets ok")
