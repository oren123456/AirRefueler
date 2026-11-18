import unreal
lsb = unreal.LevelSequenceEditorBlueprintLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
hoses = {a.get_actor_label(): a for a in eas.get_all_level_actors() if a.get_actor_label().startswith("Hose_")}
tank = next(a for a in eas.get_all_level_actors() if a.get_actor_label() == "bo_767")
for fr in [0, 300, 600, 700, 900, 1200, 1400, 1550, 1700, 1990]:
    lsb.set_current_time(fr)
    row = []
    for n, a in sorted(hoses.items()):
        c = a.skeletal_mesh_component
        row.append("%s morph=%.2f" % (n, c.get_morph_target("OUT_BLEND")))
    r = tank.get_actor_rotation()
    unreal.log("[HoseChk] frame %d  %s  tanker rot p=%.1f y=%.1f r=%.1f" % (fr, " | ".join(row), r.pitch, r.yaw, r.roll))
