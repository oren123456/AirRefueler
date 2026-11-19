"""Delete the Maya rig control boards: Mirage Panel_Manipulator (+ sliders/labels) and the Su-30
Sliders_xx controls. Sliders_24 is NOT deleted: the whole Su-30 hangs under it (its panel mesh stays hidden)."""
import unreal
SEQ = "/Game/AirRefueler/Scene/RootNode_TrackSetNode"
log = lambda *a: unreal.log("[RigPanels] " + " ".join(str(x) for x in a))
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = eas.get_all_level_actors()
kids = {}
for a in actors:
    p = a.get_attach_parent_actor()
    if p:
        kids.setdefault(p.get_path_name(), []).append(a)

def is_root(a):
    l = a.get_actor_label()
    if l == "Panel_Manipulator":
        return True
    return l.startswith("Sliders_") and l != "Sliders_24" and "MayaHidden" in [str(t) for t in a.tags]

doomed = []
def collect(a):
    doomed.append(a)
    for k in kids.get(a.get_path_name(), []):
        collect(k)
for a in actors:
    if is_root(a):
        collect(a)

labels = [a.get_actor_label() for a in doomed]
bad = [l for l in labels if l in ("Sliders_24", "Body1", "suchoi_ConstGrp", "Mirage_2000N", "Housing")]
if bad or len(doomed) > 300:
    log("ABORT, unexpected actors in the delete set:", bad, "count", len(doomed))
else:
    seq = unreal.load_asset(SEQ)
    lab = set(labels)
    nb = 0
    for b in list(seq.get_bindings()):
        if str(b.get_display_name()) in lab:
            b.remove()
            nb += 1
    with unreal.ScopedEditorTransaction("Delete rig control panels"):
        for a in reversed(doomed):
            eas.destroy_actor(a)
    unreal.EditorAssetLibrary.save_loaded_asset(seq)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    log("deleted", len(doomed), "actors, removed", nb, "sequence bindings")
    log("labels:", sorted(lab))
