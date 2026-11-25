"""Front-panel materials/textures + mesh UV info -> Saved/ClaudeShots/panel_probe.txt"""
import unreal
eal = unreal.EditorAssetLibrary; mel = unreal.MaterialEditingLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
out = []
for p in ["/Game/AirRefueler/Materials/MI_Salon_VRay1", "/Game/AirRefueler/Materials/MI_Salon_VRay1_Cutout"]:
    mi = eal.load_asset(p)
    par = mi.get_editor_property("parent")
    out.append("%s parent=%s" % (p, par.get_path_name() if par else None))
    if par and isinstance(par, unreal.Material):
        out.append("  blend=%s shading=%s two_sided=%s" % (par.get_editor_property("blend_mode"), par.get_editor_property("shading_model"), par.get_editor_property("two_sided")))
        for prop in ["MP_BASE_COLOR", "MP_ROUGHNESS", "MP_SPECULAR", "MP_METALLIC", "MP_OPACITY_MASK", "MP_NORMAL", "MP_EMISSIVE_COLOR"]:
            e = mel.get_material_property_input_node(par, getattr(unreal.MaterialProperty, prop))
            out.append("  %s <- %s" % (prop, e.get_class().get_name() if e else None))
        for e in [x for x in unreal.MaterialEditingLibrary.get_child_expressions(par)] if hasattr(unreal.MaterialEditingLibrary, "get_child_expressions") else []:
            pass
    for tp in mi.get_editor_property("texture_parameter_values"):
        t = tp.get_editor_property("parameter_value")
        out.append("  tex %s = %s %sx%s" % (tp.get_editor_property("parameter_info").get_editor_property("name"), t.get_path_name() if t else None,
                   t.blueprint_get_size_x() if t else 0, t.blueprint_get_size_y() if t else 0))
    for sp in mi.get_editor_property("scalar_parameter_values"):
        out.append("  scalar %s = %s" % (sp.get_editor_property("parameter_info").get_editor_property("name"), sp.get_editor_property("parameter_value")))
for a in eas.get_all_level_actors():
    if a.get_actor_label() in ("Cockpit_Panel", "Devices", "Cockpit", "Control_Device"):
        m = a.static_mesh_component.static_mesh
        out.append("%s %s verts=%d sections=%d mats=%s" % (a.get_actor_label(), m.get_name(), m.get_num_vertices(0), m.get_num_sections(0), [a.static_mesh_component.get_material(i).get_name() for i in range(a.static_mesh_component.get_num_materials())]))
open(unreal.Paths.project_saved_dir() + "ClaudeShots/panel_probe.txt", "w").write("\n".join(out))
