"""Place the refuel simulator in L_RefuelScene: pawn (with the Mirage attached), hose at the right pod, game mode, defaults."""
import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
eal = unreal.EditorAssetLibrary
log = lambda *x: unreal.log("[SimPlace] " + " ".join(str(v) for v in x))
SIM = "/Game/AirRefueler/Sim/"
pawn_bp = eal.load_asset(SIM + "BP_MiragePawn"); hose_bp = eal.load_asset(SIM + "BP_RefuelHose"); gm_bp = eal.load_asset(SIM + "BP_RefuelGameMode")
acts = {a.get_actor_label(): a for a in eas.get_all_level_actors()}

# cable look/feel (BP defaults)
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem); SDL = unreal.SubobjectDataBlueprintFunctionLibrary
for h in sds.k2_gather_subobject_data_for_blueprint(hose_bp):
    o = SDL.get_object(SDL.get_data(h))
    if isinstance(o, unreal.CableComponent):
        for k, v in dict(cable_force=unreal.Vector(0, -900, 0), enable_stiffness=True, enable_collision=False, num_segments=30,
                         solver_iterations=10, cable_width=7.0, tile_material=8.0).items():
            try: o.set_editor_property(k, v)
            except Exception as e: log("prop", k, e)
        hs = acts.get("Hose_RightPod")
        if hs:
            sk = hs.get_component_by_class(unreal.SkeletalMeshComponent)
            mats = sk.get_materials() if sk else []
            if mats: o.set_material(0, mats[0]); log("hose material", mats[0].get_name())
unreal.BlueprintEditorLibrary.compile_blueprint(hose_bp); eal.save_loaded_asset(hose_bp)

for lbl in ("SimPlayer_Mirage", "SimHose_RightPod"):
    if lbl in acts:
        if lbl == "SimPlayer_Mirage" and "Mirage_2000N" in acts:
            acts["Mirage_2000N"].detach_from_actor(unreal.DetachmentRule.KEEP_WORLD, unreal.DetachmentRule.KEEP_WORLD, unreal.DetachmentRule.KEEP_WORLD)
        eas.destroy_actor(acts[lbl])

p = eas.spawn_actor_from_object(pawn_bp, unreal.Vector(1682.6, -9933.1, -224.0), unreal.Rotator())
p.set_actor_label("SimPlayer_Mirage")
p.set_editor_property("auto_possess_player", unreal.AutoReceiveInput.PLAYER0)
acts["Mirage_2000N"].attach_to_actor(p, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)

h = eas.spawn_actor_from_object(hose_bp, unreal.Vector(1657.6, -299.1, 333.1), unreal.Rotator())
h.set_actor_label("SimHose_RightPod")

for lbl in ("Hose_RightPod", "Hose_LeftPod"):
    if lbl in acts:
        acts[lbl].set_actor_hidden_in_game(True)

ws = unreal.EditorLevelLibrary.get_editor_world().get_world_settings()
ws.set_editor_property("default_game_mode", gm_bp.generated_class())
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
log("placed pawn + hose, game mode set, level saved")
