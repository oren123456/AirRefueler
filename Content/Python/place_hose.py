"""Place the animated hose (Hose_N_drouge_INout_Animated) on the tanker's right wing pod.
The hose was modelled in place in Maya at the right pod (In_MAIN offset -1656,-339,305 Maya = UE 1656,-305,339)
with the OUT_BLEND morph trailing it ~35 m back to the right-pod drogue. Attaches to pod1 so it flies with the
tanker, adds a skeletal-animation track to the scene Level Sequence (deploy 0 -> 24 s). Re-runnable."""
import unreal

LABEL = "Hose_RightPod"
MESH = "/Game/AirRefueler/Hose/Hose_N_drouge_INout_Animated"
ANIM = "/Game/AirRefueler/Hose/Hose_N_drouge_INout_Animated_Anim"
SEQ = "/Game/AirRefueler/Scene/RootNode_TrackSetNode"
LOC = unreal.Vector(1656.0, -305.0, 339.0)
log = lambda *a: unreal.log("[Hose] " + " ".join(str(x) for x in a))

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = eas.get_all_level_actors()
for a in actors:
    if a.get_actor_label() == LABEL:
        eas.destroy_actor(a)
pod = next(a for a in eas.get_all_level_actors() if a.get_actor_label() == "pod1")
skm = unreal.load_asset(MESH)
anim = unreal.load_asset(ANIM)

with unreal.ScopedEditorTransaction("Place animated hose"):
    hose = eas.spawn_actor_from_object(skm, LOC, unreal.Rotator(0, 0, 0))
    hose.set_actor_label(LABEL)
    comp = hose.skeletal_mesh_component
    comp.set_editor_property("bounds_scale", 12.0)      # morph trails ~35 m past the ref-pose bounds
    comp.set_editor_property("cast_shadow", True)
    comp.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    data = unreal.SingleAnimationPlayData()
    data.set_editor_property("anim_to_play", anim)
    data.set_editor_property("saved_looping", False)
    data.set_editor_property("saved_playing", False)
    data.set_editor_property("saved_position", anim.get_play_length())   # show it deployed in the editor
    comp.set_editor_property("animation_data", data)
    comp.set_animation(anim)
    comp.set_position(anim.get_play_length(), False)
    hose.attach_to_actor(pod, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD,
                         unreal.AttachmentRule.KEEP_WORLD, False)

b_origin, b_ext = hose.get_actor_bounds(False)
log("placed", LABEL, "bounds min", b_origin - b_ext, "max", b_origin + b_ext, "attached to", pod.get_actor_label())

# Level Sequence track
seq = unreal.load_asset(SEQ)
for bnd in seq.get_bindings():
    if str(bnd.get_display_name()) == LABEL:
        bnd.remove()
binding = seq.add_possessable(hose)
track = binding.add_track(unreal.MovieSceneSkeletalAnimationTrack)
section = track.add_section()
params = section.get_editor_property("params")
params.set_editor_property("animation", anim)
section.set_editor_property("params", params)
fps = seq.get_display_rate()
frames = int(round(anim.get_play_length() * fps.numerator / fps.denominator))
section.set_range(0, frames)
log("sequence track added: frames 0 -", frames, "at", fps.numerator, "/", fps.denominator, "fps")
unreal.EditorAssetLibrary.save_loaded_asset(seq)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
log("done")
