import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
lo, hi = unreal.Vector(-1738.0, -4570.0, 236.0), unreal.Vector(-1716.0, -4552.0, 260.0)
res = []
for a in eas.get_all_level_actors():
    for c in a.get_components_by_class(unreal.PrimitiveComponent):
        try:
            o, e, r = unreal.SystemLibrary.get_component_bounds(c)
        except Exception as ex:
            continue
        if o.x - e.x > hi.x or o.x + e.x < lo.x or o.y - e.y > hi.y or o.y + e.y < lo.y or o.z - e.z > hi.z or o.z + e.z < lo.z: continue
        m = getattr(c, "static_mesh", None)
        res.append("%s/%s %s %s ext=%s" % (a.get_actor_label(), c.get_name(), c.get_class().get_name(), m.get_name() if m else "", [round(e.x), round(e.y), round(e.z)]))
unreal.log("[UfcpWho] " + " | ".join(res))
