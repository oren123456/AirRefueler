import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
out = []
for a in eas.get_all_level_actors():
    if isinstance(a, unreal.SkyLight):
        c = a.light_component
        for n in ["intensity", "real_time_capture", "source_type", "lower_hemisphere_is_black", "lower_hemisphere_color", "cast_shadows", "indirect_lighting_intensity", "volumetric_scattering_intensity", "sky_distance_threshold", "capture_emissive_only", "light_color"]:
            try: out.append("sky.%s = %s" % (n, c.get_editor_property(n)))
            except Exception as e: out.append("sky.%s ERR" % n)
    if isinstance(a, unreal.DirectionalLight):
        c = a.light_component; out.append("sun rot %s" % a.get_actor_rotation())
        for n in ["intensity", "light_source_angle", "indirect_lighting_intensity", "contact_shadow_length", "cast_shadows", "atmosphere_sun_light"]:
            try: out.append("sun.%s = %s" % (n, c.get_editor_property(n)))
            except Exception: out.append("sun.%s ERR" % n)
    if isinstance(a, unreal.PostProcessVolume):
        st = a.get_editor_property("settings"); out.append("pp unbound=%s" % a.get_editor_property("unbound"))
        for n in dir(st):
            if n.startswith("override_") and st.get_editor_property(n):
                v = n[len("override_"):]
                try: out.append("pp.%s = %s" % (v, st.get_editor_property(v)))
                except Exception: out.append("pp.%s (override on)" % v)
open(unreal.Paths.project_saved_dir() + "ClaudeShots/light_probe.txt", "w").write("\n".join(out))
