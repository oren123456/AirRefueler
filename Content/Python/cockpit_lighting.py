"""Cockpit lighting: local exposure (opens the shadowed cockpit like the eye adapts, keeps the bright outside), Lumen
tuned for small cockpit detail + a little sky leaking into fully occluded corners, sun contact shadows (switches,
knobs). Logs every setting it could / could not apply. Re-runnable."""
import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
log = lambda s: unreal.log("[Lighting] " + s)
pp = next(a for a in eas.get_all_level_actors() if isinstance(a, unreal.PostProcessVolume))
pp.modify(); st = pp.get_editor_property("settings")
WANT = {
    "local_exposure_highlight_contrast_scale": 0.8,
    "local_exposure_shadow_contrast_scale": 0.62,
    "local_exposure_detail_strength": 1.15,
    "local_exposure_blurred_luminance_blend": 0.6,
    "lumen_scene_detail": 2.0,
    "lumen_scene_lighting_quality": 2.0,
    "lumen_final_gather_quality": 2.0,
    "lumen_skylight_leaking": 0.06,
    "lumen_full_skylight_leaking_distance": 200.0,
    "bloom_intensity": 0.5,
}
for k, v in WANT.items():
    try:
        st.set_editor_property(k, v); st.set_editor_property("override_" + k, True); log("set %s = %s" % (k, v))
    except Exception as e:
        log("SKIP %s (%s)" % (k, str(e)[:80]))
pp.set_editor_property("settings", st)
sun = next(a for a in eas.get_all_level_actors() if isinstance(a, unreal.DirectionalLight)).light_component
sun.modify(); sun.set_editor_property("contact_shadow_length", 0.03); log("sun contact shadows 0.03")
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
log("done")
