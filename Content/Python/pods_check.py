"""PIE check for the two pods: per-hose state / drogue position / nearest flag / fuel."""
import unreal
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
hs = [a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor) if a.get_class().get_name().startswith("BP_RefuelHose")]
for h in hs:
    dp = h.get_editor_property("DP")
    unreal.log("[PodsCheck] %s state=%s nearest=%s fuel=%.0f DP=(%.0f,%.0f,%.0f) pod=(%.0f,%.0f,%.0f)" % (h.get_actor_label(), h.get_editor_property("State"), h.get_editor_property("Nearest"), h.get_editor_property("Fuel"), dp.x, dp.y, dp.z, *[getattr(h.get_actor_location(), k) for k in "xyz"]))
unreal.log("[PodsCheck] hoses %d" % len(hs))
