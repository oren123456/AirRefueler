"""Remove the Maya V-Ray cloud groups and set up Unreal volumetric clouds for the refuelling shot.
- Deletes Clouds_Forground_1 / Clouds_Forground__2 / Clouds_Midground_1 and their 27 VRayVolumeGrid
  children (empty actors) plus their Level Sequence bindings.
- Duplicates the engine cloud material instance into the project (never edit /Engine content) and tunes it
  for a broken cumulus deck below the formation: aircraft ~6 km, cloud base 1.5 km, tops ~4.5 km.
Re-runnable."""
import unreal

ROOTS = ["Clouds_Forground_1", "Clouds_Forground__2", "Clouds_Midground_1"]
SEQ = "/Game/AirRefueler/Scene/RootNode_TrackSetNode"
SRC_MI = "/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud_Inst"
DST_MI = "/Game/AirRefueler/Maps/MI_VolumetricCloud_Refuel"
log = lambda *a: unreal.log("[Clouds] " + " ".join(str(x) for x in a))
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

# ---- 1. remove Maya cloud actors + sequence bindings
actors = eas.get_all_level_actors()
kids = {}
for a in actors:
    p = a.get_attach_parent_actor()
    if p:
        kids.setdefault(p.get_path_name(), []).append(a)
doomed = []
def collect(a):
    doomed.append(a)
    for k in kids.get(a.get_path_name(), []):
        collect(k)
for a in actors:
    if a.get_actor_label() in ROOTS:
        collect(a)
labels = {a.get_actor_label() for a in doomed}

seq = unreal.load_asset(SEQ)
removed_b = 0
for b in list(seq.get_bindings()):
    if str(b.get_display_name()) in labels:
        b.remove()
        removed_b += 1
with unreal.ScopedEditorTransaction("Remove Maya clouds"):
    for a in reversed(doomed):
        eas.destroy_actor(a)
eal.save_loaded_asset(seq)
log("deleted actors:", len(doomed), "sequence bindings removed:", removed_b)

# ---- 2. project copy of the cloud material
if not eal.does_asset_exist(DST_MI):
    eal.duplicate_asset(SRC_MI, DST_MI)
mi = eal.load_asset(DST_MI)
S = lambda n, v: mel.set_material_instance_scalar_parameter_value(mi, n, v)
V = lambda n, c: mel.set_material_instance_vector_parameter_value(mi, n, unreal.LinearColor(*c))
S("Cloud_GlobalCoverage", -0.15)      # broken cumulus, ground visible between the cells
S("Cloud_GlobalDensity", 0.010)
S("Layout_CloudGlobalScale", 220.0)   # tighter cells -> reads as cumulus, not stratus
V("Cloud_AlbedoColor", (0.97, 0.97, 0.98, 0.5))
V("Layout_WindControls", (1.0, 0.3, 0.5, 0.333))   # slow drift
mel.update_material_instance(mi)
eal.save_loaded_asset(mi)

# ---- 3. cloud component
cloud = next(a for a in eas.get_all_level_actors() if isinstance(a, unreal.VolumetricCloud))
c = cloud.get_component_by_class(unreal.VolumetricCloudComponent)
c.modify()
c.set_editor_property("material", mi)
c.set_editor_property("layer_bottom_altitude", 1.5)    # km
c.set_editor_property("layer_height", 3.0)             # km -> tops at 4.5 km, ~1.5 km under the aircraft
c.set_editor_property("tracing_max_distance", 250.0)   # km, deck visible to the horizon from 6 km
c.set_editor_property("tracing_start_max_distance", 400.0)
c.set_editor_property("view_sample_count_scale", 1.5)
c.set_editor_property("shadow_view_sample_count_scale", 1.0)
c.set_editor_property("sky_light_cloud_bottom_occlusion", 0.6)
log("cloud component:", cloud.get_actor_label(), "material", mi.get_path_name())

# sun: clouds and atmosphere shadowed by clouds
sun = next(a for a in eas.get_all_level_actors() if isinstance(a, unreal.DirectionalLight))
lc = sun.get_component_by_class(unreal.DirectionalLightComponent)
lc.modify()
lc.set_editor_property("cast_cloud_shadows", True)
lc.set_editor_property("cast_shadows_on_clouds", True)
lc.set_editor_property("cast_shadows_on_atmosphere", True)

# atmosphere: haze toward the horizon comes from aerial perspective, not height fog.
# The height fog sat at ground level 6 km below and drew a dark band along the horizon -> removed.
sky = next(a for a in eas.get_all_level_actors() if isinstance(a, unreal.SkyAtmosphere)).get_component_by_class(unreal.SkyAtmosphereComponent)
sky.modify()
sky.set_editor_property("aerial_pespective_view_distance_scale", 4.0)
sky.set_editor_property("ground_albedo", unreal.Color(r=190, g=196, b=205, a=255))
for f in [a for a in eas.get_all_level_actors() if isinstance(a, unreal.ExponentialHeightFog)]:
    eas.destroy_actor(f)
sun.set_editor_property("intensity", 12000.0)
pp = next(a for a in eas.get_all_level_actors() if isinstance(a, unreal.PostProcessVolume))
pp.modify()
st = pp.get_editor_property("settings")
st.set_editor_property("auto_exposure_max_brightness", 11.5)   # keeps Lumen's cached-lighting range happy
pp.set_editor_property("settings", st)
unreal.SystemLibrary.execute_console_command(None, "r.VolumetricCloud.ApplyFogLate 0")   # also in DefaultEngine.ini

unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
log("done")
