import unreal
mel = unreal.MaterialEditingLibrary
mi = unreal.load_asset("/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud_Inst")
unreal.log("[CloudInfo] parent %s" % mi.get_editor_property("parent").get_path_name())
for n in mel.get_scalar_parameter_names(mi):
    unreal.log("[CloudInfo] scalar %s = %s" % (n, mel.get_material_instance_scalar_parameter_value(mi, n)))
for n in mel.get_vector_parameter_names(mi):
    unreal.log("[CloudInfo] vector %s = %s" % (n, mel.get_material_instance_vector_parameter_value(mi, n)))
for n in mel.get_texture_parameter_names(mi):
    t = mel.get_material_instance_texture_parameter_value(mi, n)
    unreal.log("[CloudInfo] texture %s = %s" % (n, t.get_path_name() if t else None))
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
kids = {}
for a in eas.get_all_level_actors():
    p = a.get_attach_parent_actor()
    if p: kids.setdefault(p.get_path_name(), []).append(a)
def walk(a, d=0):
    n = len(a.get_components_by_class(unreal.PrimitiveComponent))
    unreal.log("[CloudInfo] %s%s (%s) prims=%d" % ("  " * d, a.get_actor_label(), a.get_class().get_name(), n))
    for k in kids.get(a.get_path_name(), []): walk(k, d + 1)
for a in eas.get_all_level_actors():
    if a.get_actor_label() in ("Clouds_Forground_1", "Clouds_Forground__2", "Clouds_Midground_1"):
        walk(a)
