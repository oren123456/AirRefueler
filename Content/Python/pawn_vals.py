import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
out = []
for a in eas.get_all_level_actors():
    if a.get_class().get_name().startswith("BP_MiragePawn"):
        for n in ["KThr", "Velocity", "CamYaw", "CamPitch", "LockCount"]:
            out.append("%s = %s" % (n, a.get_editor_property(n)))
open(unreal.Paths.project_saved_dir() + "ClaudeShots/pawn_vals.txt", "w").write("\n".join(out))
