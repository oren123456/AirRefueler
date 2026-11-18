"""Add 'hold fully out' sections to the hose animation tracks so the pose doesn't depend on
Keep-State behaviour (scrubbing in the editor showed stale poses). A hold section plays only the
last frame of the anim, looped over the gap. Re-runnable: removes previous holds first."""
import unreal

SEQ = "/Game/AirRefueler/Scene/RootNode_TrackSetNode"
ANIM = "/Game/AirRefueler/Hose/Hose_N_drouge_INout_Animated_Anim"
HOLDS = {"Hose_RightPod": [(600, 2001)], "Hose_LeftPod": [(600, 1400)]}
log = lambda *a: unreal.log("[HoseHold] " + " ".join(str(x) for x in a))

seq = unreal.load_asset(SEQ)
anim = unreal.load_asset(ANIM)
tick = seq.get_tick_resolution()
disp = seq.get_display_rate()
length = anim.get_play_length()
last_frame_ticks = int(round((length - float(disp.denominator) / disp.numerator) * tick.numerator / tick.denominator))

for b in seq.get_bindings():
    name = str(b.get_display_name())
    if name not in HOLDS:
        continue
    for tr in b.find_tracks_by_type(unreal.MovieSceneSkeletalAnimationTrack):
        for s in list(tr.get_sections()):
            if s.get_editor_property("params").get_editor_property("start_frame_offset").value > 0:
                tr.remove_section(s)
        for start, end in HOLDS[name]:
            s = tr.add_section()
            p = s.get_editor_property("params")
            p.set_editor_property("animation", anim)
            p.set_editor_property("start_frame_offset", unreal.FrameNumber(last_frame_ticks))
            s.set_editor_property("params", p)
            s.set_range(start, end)
            s.set_row_index(1)
        log(name, "sections:", [(sec.get_start_frame(), sec.get_end_frame(),
             sec.get_editor_property("params").get_editor_property("reverse")) for sec in tr.get_sections()])
unreal.EditorAssetLibrary.save_loaded_asset(seq)
log("done; tick", tick.numerator, "hold offset ticks", last_frame_ticks)
