import unreal
mi = unreal.load_asset("/Game/AirRefueler/Maps/MI_VolumetricCloud_Refuel")
mel = unreal.MaterialEditingLibrary
unreal.log("[CloudParams] scalar " + ", ".join(str(n) for n in mel.get_scalar_parameter_names(mi)))
unreal.log("[CloudParams] vector " + ", ".join(str(n) for n in mel.get_vector_parameter_names(mi)))
sun = next(a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() if isinstance(a, unreal.DirectionalLight)).light_component
unreal.log("[CloudParams] sun cast_cloud_shadows=%s cloud_scattered_luminance_scale=%s" % (sun.get_editor_property("cast_cloud_shadows"), sun.get_editor_property("cloud_scattered_luminance_scale")))
