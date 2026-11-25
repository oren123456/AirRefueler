"""Plug the parachute's throat with a collision sphere (the coupling): centre x=-36 (mesh space, hub at origin,
basket toward -X), radius 13 -> surface at x=-49 on the axis. Then trace the axis to verify."""
import unreal
eal = unreal.EditorAssetLibrary
log = lambda s: unreal.log("[Plug] " + s)
sm = eal.load_asset("/Game/AirRefueler/Models/Drogue/SM_Drogue_Parachute")
bs = sm.get_editor_property("body_setup")
ag = bs.get_editor_property("agg_geom")
sph = list(ag.get_editor_property("sphere_elems"))
log("before: convex=%d spheres=%d" % (len(ag.get_editor_property("convex_elems")), len(sph)))
if not sph:
    e = unreal.KSphereElem()
    e.set_editor_property("center", unreal.Vector(-36.0, 0.0, 0.0))
    e.set_editor_property("radius", 13.0)
    try: e.set_editor_property("name", "Coupling")
    except Exception: pass
    sph.append(e)
    ag.set_editor_property("sphere_elems", sph)
    bs.set_editor_property("agg_geom", ag)
    sm.modify()
    try: sm.post_edit_change()
    except Exception as ex: log("post_edit_change %s" % ex)
    eal.save_loaded_asset(sm, False)
ag = sm.get_editor_property("body_setup").get_editor_property("agg_geom")
log("after: convex=%d spheres=%d" % (len(ag.get_editor_property("convex_elems")), len(ag.get_editor_property("sphere_elems"))))
