"""Line-trace the placed parachute (editor world) along its axis at several radii; report where the collision is hit."""
import unreal, math
w = unreal.EditorLevelLibrary.get_editor_world()
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
hose = [a for a in eas.get_all_level_actors() if a.get_actor_label() == "SimHose_LeftPod"][0]
par = [c for c in hose.get_components_by_class(unreal.StaticMeshComponent) if c.get_name() == "Parachute"][0]
xf = par.get_world_transform()
res = []
for r in (0.0, 10.0, 18.0, 25.0, 32.0, 38.0):
    for ang in (0, 90, 180, 270):
        y = r * math.cos(math.radians(ang)); z = r * math.sin(math.radians(ang))
        a = xf.transform_location(unreal.Vector(-150.0, y, z)); b = xf.transform_location(unreal.Vector(20.0, y, z))
        r_ = par.line_trace_component(a, b, False, False, False)
        try:
            ok = r_[0] if isinstance(r_, tuple) else r_
            loc = [v for v in (r_ if isinstance(r_, tuple) else []) if isinstance(v, unreal.Vector)]
            blocking = bool(ok)
            lx = xf.inverse_transform_location(loc[0]).x if (blocking and loc) else None
        except Exception as e:
            blocking, lx = str(e)[:80], None
        res.append("r=%g a=%d hit=%s x=%s" % (r, ang, blocking, None if lx is None else round(lx, 1)))
unreal.log("[ChuteTrace] " + " | ".join(res))
