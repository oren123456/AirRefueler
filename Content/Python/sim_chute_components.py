"""BP_RefuelHose: replace DrogueMesh with Parachute (physics, collision) + Body (visual).
BP_MiragePawn: add capsule colliders (Col_*) the parachute bumps into. Collision shapes are editable in the BPs / mesh editor."""
import unreal
eal = unreal.EditorAssetLibrary
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem); SDL = unreal.SubobjectDataBlueprintFunctionLibrary
log = lambda *x: unreal.log("[ChuteComps] " + " ".join(str(v) for v in x))

def comps(bp):
    out = {}
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        o = SDL.get_object(SDL.get_data(h))
        if o: out[o.get_name().replace("_GEN_VARIABLE", "")] = (h, o)
    return out

def add(bp, parent, cls, name):
    c = comps(bp)
    if name in c: return c[name][1]
    h, fail = sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=c[parent][0], new_class=cls, blueprint_context=bp))
    sds.rename_subobject(h, unreal.Text(name))
    return SDL.get_object(SDL.get_data(h))

def rot(p=0.0, y=0.0, r=0.0):
    x = unreal.Rotator(); x.pitch = p; x.yaw = y; x.roll = r; return x

# ---------------- hose
hose = eal.load_asset("/Game/AirRefueler/Sim/BP_RefuelHose")
c = comps(hose); log("hose comps", list(c.keys()))
root = [k for k, (h, o) in c.items() if isinstance(o, unreal.SceneComponent) and k in ("DefaultSceneRoot", "PodExit")][0]
chute = add(hose, root, unreal.StaticMeshComponent, "Parachute")
chute.set_editor_property("static_mesh", eal.load_asset("/Game/AirRefueler/Sim/SM_Drogue_Parachute"))
chute.set_collision_profile_name("PhysicsActor")
chute.set_editor_property("generate_overlap_events", False)
bi = chute.get_editor_property("body_instance")
for k, v in dict(simulate_physics=True, enable_gravity=False, use_ccd=True, linear_damping=0.2, angular_damping=8.0,
                 override_mass=True, mass_in_kg_override=25.0).items():
    try: bi.set_editor_property(k, v)
    except Exception as e: log("bi", k, e)
chute.set_editor_property("body_instance", bi)
body = add(hose, "Parachute", unreal.StaticMeshComponent, "Body")
body.set_editor_property("static_mesh", eal.load_asset("/Game/AirRefueler/Sim/SM_Drogue_Body"))
body.set_collision_profile_name("NoCollision")
c = comps(hose)
if "DrogueMesh" in c:
    sds.delete_subobjects(c[root][0], [c["DrogueMesh"][0]], hose)
    log("DrogueMesh removed")
if "Hose" in c:
    c["Hose"][1].set_collision_profile_name("NoCollision")
unreal.BlueprintEditorLibrary.compile_blueprint(hose); eal.save_loaded_asset(hose)

# ---------------- pawn colliders (pawn-local, Mirage nose = +Y). Capsule axis is Z -> roll 90 lays it along Y.
pawn = eal.load_asset("/Game/AirRefueler/Sim/BP_MiragePawn")
pc = comps(pawn)
proot = [k for k, (h, o) in pc.items() if isinstance(o, unreal.SceneComponent) and k in ("DefaultSceneRoot", "Root")][0]
COLS = {  # name: (centre, radius, half height)
    "Col_Nose":     ((2.4, 600.0, -110.0), 28.0, 125.0),
    "Col_Forward":  ((2.4, 430.0, -98.0), 46.0, 90.0),
    "Col_Canopy":   ((2.4, 265.0, -15.0), 44.0, 130.0),
    "Col_Fuselage": ((2.4, 240.0, -100.0), 55.0, 170.0),
}
for name, ((x, y, z), r, hh) in COLS.items():
    cap = add(pawn, proot, unreal.CapsuleComponent, name)
    cap.set_editor_property("relative_location", unreal.Vector(x, y, z))
    cap.set_editor_property("relative_rotation", rot(r=90.0))
    cap.set_editor_property("capsule_radius", r)
    cap.set_editor_property("capsule_half_height", hh)
    cap.set_collision_profile_name("BlockAllDynamic")
    cap.set_editor_property("hidden_in_game", True)
    cap.set_editor_property("generate_overlap_events", False)
unreal.BlueprintEditorLibrary.compile_blueprint(pawn); eal.save_loaded_asset(pawn)
log("done", list(comps(hose).keys()), list(comps(pawn).keys()))
