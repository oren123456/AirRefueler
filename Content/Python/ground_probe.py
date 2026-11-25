import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
out = []
for a in eas.get_all_level_actors():
    c = a.get_class().get_name()
    if any(k in c for k in ["Sky", "Cloud", "Light", "Fog", "Pawn", "BP_", "StaticMesh", "PostProcess"]) or "767" in a.get_actor_label():
        out.append("%s | %s | %s" % (a.get_actor_label(), c, a.get_actor_location()))
sky = next(a for a in eas.get_all_level_actors() if isinstance(a, unreal.SkyAtmosphere)).get_component_by_class(unreal.SkyAtmosphereComponent)
for p in ["transform_mode", "bottom_radius", "atmosphere_height", "ground_albedo", "aerial_pespective_view_distance_scale"]:
    out.append("sky.%s = %s" % (p, sky.get_editor_property(p)))
out.append("sky comp loc %s" % sky.get_world_location())
open(unreal.Paths.project_saved_dir() + "ClaudeShots/ground_probe.txt", "w").write("\n".join(out))
