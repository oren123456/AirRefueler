"""Remove the cumulus puffs (CloudPuff-tagged actors) and the CloudStream mover from the level, then save it.
Assets M_CloudPuff / BP_CloudStream stay in Sim/Clouds (unused); re-run cloud_puffs.py to bring them back."""
import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
n = 0
for a in eas.get_all_level_actors():
    if a.actor_has_tag("CloudPuff") or a.get_actor_label() == "CloudStream" or a.get_class().get_name().startswith("BP_CloudStream"):
        eas.destroy_actor(a); n += 1
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
left = [a.get_actor_label() for a in eas.get_all_level_actors() if a.actor_has_tag("CloudPuff") or a.get_class().get_name().startswith("BP_CloudStream")]
unreal.log("[PuffsRemove] removed %d, left %d %s" % (n, len(left), left))
