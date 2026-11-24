import unreal, json
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
out = []
for a in eas.get_all_level_actors():
    l = a.get_actor_label()
    if "Hose" in l or "Drog" in l or "drog" in l or "Sim" in l or isinstance(a, unreal.SkeletalMeshActor):
        d = {"label": l, "name": a.get_name(), "class": a.get_class().get_name(), "loc": str(a.get_actor_location()), "hidden_game": a.is_hidden_ed() if False else a.get_editor_property("hidden"),
             "parent": a.get_attach_parent_actor().get_actor_label() if a.get_attach_parent_actor() else None, "comps": []}
        for c in a.get_components_by_class(unreal.PrimitiveComponent):
            e = {"name": c.get_name(), "cls": c.get_class().get_name(), "coll": str(c.get_collision_enabled()), "profile": str(c.get_collision_profile_name())}
            if isinstance(c, unreal.SkeletalMeshComponent):
                sk = c.get_editor_property("skeletal_mesh_asset") if hasattr(c, "get_skeletal_mesh_asset") or True else None
                try: e["mesh"] = c.get_skeletal_mesh_asset().get_path_name()
                except Exception: 
                    try: e["mesh"] = c.skeletal_mesh.get_path_name()
                    except Exception as ex: e["mesh"] = str(ex)
                try: e["phys"] = c.get_editor_property("physics_asset_override").get_path_name() if c.get_editor_property("physics_asset_override") else None
                except Exception as ex: e["phys"] = str(ex)
            if isinstance(c, unreal.StaticMeshComponent) and c.static_mesh:
                e["mesh"] = c.static_mesh.get_path_name()
            d["comps"].append(e)
        out.append(d)
json.dump(out, open(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()) + "ClaudeShots/hoses.json", "w"), indent=1)
unreal.log("[InspectHoses] %d" % len(out))
