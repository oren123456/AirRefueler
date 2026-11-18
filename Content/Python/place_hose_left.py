"""Left wing pod hose: copy of Hose_RightPod (the asset was modelled for the right pod).
Placed at the mirrored pod position, shifted by the pod1 -> pod2 offset
(the left pod mesh sits ~73 cm lower than a pure mirror). Attached to pod2.
Sequence: let out 0-24 s, hold, reel in 56-80 s (same anim played in reverse). Re-runnable."""
import unreal

LABEL = "Hose_LeftPod"
RIGHT = "Hose_RightPod"
MESH = "/Game/AirRefueler/Hose/Hose_N_drouge_INout_Animated"
ANIM = "/Game/AirRefueler/Hose/Hose_N_drouge_INout_Animated_Anim"
SEQ = "/Game/AirRefueler/Scene/RootNode_TrackSetNode"
OUT_START_S, IN_START_S = 0.0, 56.0
log = lambda *a: unreal.log("[HoseL] " + " ".join(str(x) for x in a))

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
by_label = lambda l: next((a for a in eas.get_all_level_actors() if a.get_actor_label() == l), None)
for a in eas.get_all_level_actors():
    if a.get_actor_label() == LABEL:
        eas.destroy_actor(a)

def mesh_center(label):
    a = by_label(label)
    o, e = a.get_actor_bounds(False)
    return o

right = by_label(RIGHT)
pod1, pod2 = by_label("pod1"), by_label("pod2")
c1, c2 = mesh_center("pCylinder1"), mesh_center("pCylinder11")
rl = right.get_actor_location()
offset = unreal.Vector(c2.x - (-c1.x), c2.y - c1.y, c2.z - c1.z)
loc = unreal.Vector(-rl.x + offset.x, rl.y + offset.y, rl.z + offset.z)
log("pod1 centre", c1, "pod2 centre", c2, "offset", offset, "-> location", loc)

skm = unreal.load_asset(MESH)
anim = unreal.load_asset(ANIM)
length = anim.get_play_length()
with unreal.ScopedEditorTransaction("Place left hose"):
    hose = eas.spawn_actor_from_object(skm, loc, unreal.Rotator(0, 0, 0))
    hose.set_actor_label(LABEL)
    # no mirror: a negative scale made the skinned hose render wrongly once attached to the rotated pod.
    # The tube is symmetric; only its slight sideways drift (~80 cm) goes outboard instead of inboard.
    comp = hose.skeletal_mesh_component
    comp.set_editor_property("bounds_scale", 12.0)
    comp.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    data = unreal.SingleAnimationPlayData()
    data.set_editor_property("anim_to_play", anim)
    data.set_editor_property("saved_looping", False)
    data.set_editor_property("saved_playing", False)
    data.set_editor_property("saved_position", length)      # editor view: let out
    comp.set_editor_property("animation_data", data)
    comp.set_animation(anim)
    comp.set_position(length, False)
    hose.attach_to_actor(pod2, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD,
                         unreal.AttachmentRule.KEEP_WORLD, False)

# sequence: out, hold, in
seq = unreal.load_asset(SEQ)
for bnd in seq.get_bindings():
    if str(bnd.get_display_name()) == LABEL:
        bnd.remove()
fps = seq.get_display_rate()
f = lambda s: int(round(s * fps.numerator / fps.denominator))
binding = seq.add_possessable(hose)
track = binding.add_track(unreal.MovieSceneSkeletalAnimationTrack)

def add(start_s, reverse):
    sec = track.add_section()
    p = sec.get_editor_property("params")
    p.set_editor_property("animation", anim)
    p.set_editor_property("reverse", reverse)
    sec.set_editor_property("params", p)
    sec.set_range(f(start_s), f(start_s + length))
    try:
        sec.set_completion_mode(unreal.MovieSceneCompletionMode.KEEP_STATE)
    except Exception:
        opts = sec.get_editor_property("eval_options")
        opts.set_editor_property("completion_mode", unreal.MovieSceneCompletionMode.KEEP_STATE)
        sec.set_editor_property("eval_options", opts)
    return sec

add(OUT_START_S, False)
add(IN_START_S, True)
end = seq.get_playback_end()
log("sections: out", f(OUT_START_S), "-", f(OUT_START_S + length), " in", f(IN_START_S), "-", f(IN_START_S + length),
    "| sequence end frame", end, "fps", fps.numerator, "/", fps.denominator)
unreal.EditorAssetLibrary.save_loaded_asset(seq)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
log("done")
