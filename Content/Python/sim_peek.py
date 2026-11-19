import unreal, json, sys
w = None
for f in ("get_game_world",):
    try: w = unreal.EditorLevelLibrary.get_game_world()
    except Exception as e: pass
out = {"world": w.get_name() if w else None}
if w:
    acts = unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor)
    for a in acts:
        n = a.get_class().get_name()
        if "BP_RefuelHose" in n or "BP_MiragePawn" in n:
            d = {"loc": str(a.get_actor_location())}
            for v in ("State", "HoseLen", "Fuel", "Msg", "Flowing", "Velocity", "ExtendCount", "AutoDone"):
                try: d[v] = str(a.get_editor_property(v))
                except Exception as e: pass
            for c in a.get_components_by_class(unreal.SceneComponent):
                d["c_" + c.get_name()] = str(c.get_world_location())
            d["tick"] = a.is_actor_tick_enabled() if hasattr(a, "is_actor_tick_enabled") else None
            out[n + "_" + a.get_name()] = d
if len(sys.argv) > 1 and w:
    # argv: dx dy dz vy  -> teleport pawn relative to drogue and give forward velocity
    hose = [a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor) if "BP_RefuelHose" in a.get_class().get_name()][0]
    pawn = unreal.GameplayStatics.get_player_pawn(w, 0)
    drg = [c for c in hose.get_components_by_class(unreal.SceneComponent) if c.get_name() == "Drogue"][0]
    probe = [c for c in pawn.get_components_by_class(unreal.SceneComponent) if c.get_name() == "ProbeTip"][0]
    off = drg.get_world_location() + unreal.Vector(float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3])) - probe.get_world_location()
    pawn.set_actor_location(pawn.get_actor_location() + off, False, True)
    pawn.set_editor_property("Velocity", unreal.Vector(0, float(sys.argv[4]), 0))
    out["moved"] = str(off)
json.dump(out, open(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()) + "ClaudeShots/sim_peek.json", "w"), indent=1)
