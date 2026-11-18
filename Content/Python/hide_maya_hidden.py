"""Hide the actors that were hidden in the Maya scene (hidden nodes + hidden display layers).
Interchange ignores Maya/FBX visibility, so e.g. the 767 CAD layout, the landing gear, the
Su-30 nozzle rig copies and the control sliders all show up in UE.
Paths come from maya_hidden.json (generated from Senario_full_v06.ma). Visibility is inherited
by attached children, like in Maya. Undo with Ctrl+Z, or search the outliner for tag MayaHidden."""
import json, os, re
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
paths = json.load(open(os.path.join(HERE, "maya_hidden.json"), encoding="utf-8"))
log = lambda *a: unreal.log("[MayaHidden] " + " ".join(str(x) for x in a))

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = eas.get_all_level_actors()
kids = {}
tops = []
for a in actors:
    p = a.get_attach_parent_actor()
    if p:
        kids.setdefault(p.get_path_name(), []).append(a)
    else:
        tops.append(a)
# Interchange may put the scene under a RootNode actor
for a in list(tops):
    if a.get_actor_label() == "RootNode":
        tops += kids.get(a.get_path_name(), [])


san = lambda n: re.sub(r"[^A-Za-z0-9_\-]", "_", n)


def pick(cands, name, sibling_names):
    name = san(name)
    exact = [c for c in cands if c.get_actor_label() == name]
    if len(exact) == 1:
        return exact[0]
    rx = re.compile(re.escape(name) + r"\d+$")
    fuzzy = [c for c in cands if rx.match(c.get_actor_label()) and c.get_actor_label() not in sibling_names]
    return fuzzy[0] if len(fuzzy) == 1 else (exact[0] if exact else None)


def find(path):
    parts = [p for p in path.split("|") if p]
    level = tops
    a = None
    for part in parts:
        a = pick(level, part, set())
        if a is None:
            break
        level = kids.get(a.get_path_name(), [])
    else:
        return a
    # fallback: leaf name is unique in the level
    leaf = [x for x in actors if x.get_actor_label() == san(parts[-1])]
    return leaf[0] if len(leaf) == 1 else None


hidden, missing = 0, []
with unreal.ScopedEditorTransaction("Hide Maya-hidden objects"):
    for p in paths:
        a = find(p)
        if a is None:
            missing.append(p)
            continue
        root = a.get_editor_property("root_component")
        if root:
            root.modify()
            root.set_visibility(False, True)
        a.set_actor_hidden_in_game(True)
        tags = list(a.tags)
        if "MayaHidden" not in tags:
            a.tags = tags + [unreal.Name("MayaHidden")]
        hidden += 1
log("hidden roots:", hidden, "of", len(paths))
for m in missing:
    log("NOT FOUND:", m)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
log("done")
