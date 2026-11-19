"""Delete unused actors (approved by Oren 2026-11-19):
 - 767 CAD layout (767-300_TANKER_LAYOUT_V2_stp) + group19 (hidden CAD duplicate)
 - Maya rig helpers: locator1-4, null1-3, nurbsCircle1, Boing_Ctrl3, Daynamic_DONT_TUCH(_new), TRACKER
 - Render_Grp leftovers (ground, V-Ray lights); the 'Free' camera is kept and detached
 - old scene hose/drogue rigs: group18 (hoze1), LeftWing_Pod_Main_Ctrl / HDU_Pod_Main_Ctrl2 (Drouge11/Drouge12)
Removes the Level Sequence bindings that pointed only at deleted actors."""
import unreal
log = lambda *a: unreal.log("[Cleanup] " + " ".join(str(x) for x in a))
SEQ = "/Game/AirRefueler/Scene/RootNode_TrackSetNode"
ROOTS = ["767-300_TANKER_LAYOUT_V2_stp", "group19", "locator1", "locator2", "locator3", "locator4",
         "null1", "null2", "null3", "nurbsCircle1", "Boing_Ctrl3", "Daynamic_DONT_TUCH", "Daynamic_DONT_TUCH_new",
         "TRACKER", "Render_Grp", "group18", "LeftWing_Pod_Main_Ctrl", "HDU_Pod_Main_Ctrl2"]
KEEP = {"Free"}            # camera inside Render_Grp
PROTECT = {"Boing_Ctrl", "bo_767", "pod1", "pod2", "Body1", "Mirage_2000N", "Suchoi_Ctrl", "Hose_RightPod", "Hose_LeftPod"}

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors = eas.get_all_level_actors()
kids = {}
for a in actors:
    p = a.get_attach_parent_actor()
    if p:
        kids.setdefault(p.get_path_name(), []).append(a)

# parents of the top-level Maya nodes may be a RootNode actor -> roots are matched by label anywhere at top
doomed, keep = [], []
def collect(a):
    if a.get_actor_label() in KEEP:
        keep.append(a)
        return
    doomed.append(a)
    for k in kids.get(a.get_path_name(), []):
        collect(k)
for a in actors:
    if a.get_actor_label() in ROOTS:
        p = a.get_attach_parent_actor()
        if p is None or p.get_actor_label() in ("RootNode",):
            collect(a)

labels = [a.get_actor_label() for a in doomed]
# visible meshes in the delete set must only be the old drogues
vis = [a.get_actor_label() for a in doomed for c in a.get_components_by_class(unreal.StaticMeshComponent) if c.is_visible()]
bad = [l for l in labels if l in PROTECT]
if bad or any(not v.startswith("Drouge") for v in vis):
    log("ABORT. protected:", bad, "visible meshes:", vis)
    raise SystemExit

seq = unreal.load_asset(SEQ)
doomed_set = set(a.get_path_name() for a in doomed)
rm_bindings = []
try:
    rng = seq.get_playback_range() if hasattr(seq, "get_playback_range") else None
    bound = unreal.SequencerTools.get_bound_objects(world, seq, seq.get_bindings(), seq.make_range(seq.get_playback_start(), seq.get_playback_end()))
    for bo in bound:
        objs = [o for o in bo.bound_objects if o]
        if objs and all(o.get_path_name() in doomed_set for o in objs):
            rm_bindings.append(bo.binding_proxy)
except Exception as e:
    log("bound-object lookup failed (%s); falling back to names" % e)
    lab = set(labels)
    rm_bindings = [b for b in seq.get_bindings() if str(b.get_display_name()) in lab]

with unreal.ScopedEditorTransaction("Delete unused Maya actors"):
    for k in keep:
        k.detach_from_actor(unreal.DetachmentRule.KEEP_WORLD, unreal.DetachmentRule.KEEP_WORLD, unreal.DetachmentRule.KEEP_WORLD)
    for b in rm_bindings:
        b.remove()
    for a in reversed(doomed):
        eas.destroy_actor(a)
unreal.EditorAssetLibrary.save_loaded_asset(seq)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
log("deleted actors:", len(doomed), "| bindings removed:", len(rm_bindings), "| kept:", [k.get_actor_label() for k in keep],
    "| visible meshes removed:", vis)
