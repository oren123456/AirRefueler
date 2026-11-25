import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
out = []
for a in eas.get_all_level_actors():
    l = a.get_actor_label()
    if True:
        par = a.get_attach_parent_actor()
        o, e = a.get_actor_bounds(False)
        out.append("%s [%s] loc=%s ctr=%s ext=%s hidden=%s parent=%s" % (l, a.get_class().get_name(), a.get_actor_location(), [round(o.x), round(o.y), round(o.z)], [round(e.x), round(e.y), round(e.z)], a.is_hidden_ed(), par.get_actor_label() if par else None))
unreal.log("[PodsInv] " + " || ".join(out))
