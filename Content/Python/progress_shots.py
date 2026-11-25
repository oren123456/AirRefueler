"""PIE progress screenshots (HighResShot 2). Stages the Mirage relative to the trailed drogue and moves the player
camera (PilotCam world location + CamYaw/CamPitch + FOV) for each shot. Logs '[Shots] <name>' before each capture
so the files in Saved/Screenshots/WindowsEditor can be renamed in order."""
import unreal, time, math, sys
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if unreal.EditorLevelLibrary.get_game_world() is None: les.editor_request_begin_play()
log = lambda s: unreal.log("[Shots] " + s)
st = {"t0": None, "i": 0, "tn": 0.0, "h": None, "stage": None, "shot": False}
V = unreal.Vector
def comp(a, n): return [c for c in a.get_components_by_class(unreal.SceneComponent) if c.get_name() == n][0]
# shot list: (name, mirage stage, camera mode, fov)
SHOTS = [
    ("01_cockpit_approach", "behind8m", "cockpit", 95.0),
    ("02_formation_side", "behind8m", "side", 45.0),
    ("03_chase_behind", "behind8m", "chase", 55.0),
    ("04_wide_formation", "behind8m", "wide", 40.0),
    ("05_probe_entering_basket", "entering", "close", 45.0),
    ("06_connected_closeup", "locked", "close", 45.0),
    ("07_connected_chase", "locked", "chase", 55.0),
    ("08_hose_closeup", "behind8m", "hose", 40.0),
    ("09_hud", "behind8m", "hud", 34.0),
    ("10_hud_contact", "locked", "hud", 34.0),
]
def tick(dt):
    try: _tick(dt)
    except Exception as e:
        log("ERROR %s" % e); unreal.unregister_slate_post_tick_callback(st["h"]); les.editor_request_end_play()
def aim(p, cam, cl, target, fov):
    cam.set_world_location(cl, False, True)
    r = unreal.MathLibrary.find_look_at_rotation(cl, target)
    p.set_editor_property("CamYaw", r.yaw - 90.0); p.set_editor_property("CamPitch", r.pitch)
    cam.set_field_of_view(fov)
def tanker_points(w):
    acts = unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor)
    root = [a for a in acts if a.get_actor_label() == "Boing_Ctrl"]
    pts = []
    if root:
        for a in acts:
            q = a
            while q is not None and q != root[0]: q = q.get_attach_parent_actor()
            if q is not None and isinstance(a, unreal.StaticMeshActor):
                o, e = a.get_actor_bounds(False)
                if e.length() < 1e5: pts += [o - e, o + e]
    return pts
def frame(p, cam, pts, dirv, fov, margin=1.12):
    lo = V(min(q.x for q in pts), min(q.y for q in pts), min(q.z for q in pts)); hi = V(max(q.x for q in pts), max(q.y for q in pts), max(q.z for q in pts))
    c = (lo + hi) * 0.5; R = max((q - c).length() for q in pts)
    dv = dirv * (1.0 / dirv.length())
    aim(p, cam, c + dv * (R / math.tan(math.radians(fov * 0.5)) * margin), c, fov)
def _tick(dt):
    w = unreal.EditorLevelLibrary.get_game_world()
    if w is None: return
    now = time.time()
    if st["t0"] is None: st["t0"] = now; st["tn"] = now + 2.0
    hs = [a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor) if "BP_RefuelHose" in a.get_class().get_name()]
    p = unreal.GameplayStatics.get_player_pawn(w, 0)
    if not hs or p is None: return
    h = hs[0]; drg = comp(h, "Parachute"); pr = comp(p, "ProbeTip"); cam = comp(p, "PilotCam")
    if "camrel" not in st: st["camrel"] = cam.get_editor_property("relative_location")
    S = h.get_editor_property("State"); d = drg.get_world_location(); fwd = drg.get_forward_vector(); pod = h.get_actor_location()
    loc = unreal.MathLibrary.inverse_transform_location(drg.get_world_transform(), pr.get_world_location()); r = math.hypot(loc.y, loc.z)
    if st["i"] >= len(SHOTS):
        if now > st["tn"]:
            unreal.unregister_slate_post_tick_callback(st["h"]); les.editor_request_end_play(); log("done")
        return
    name, stage, mode, fov = SHOTS[st["i"]]
    # --- stage the Mirage
    if stage != st["stage"]:
        st["stage"] = stage
        if stage in ("behind8m", "entering"):
            if S == 3: p.set_editor_property("LockCount", p.get_editor_property("LockCount") + 1)
            back = 800.0 if stage == "behind8m" else 95.0
            off = d - fwd * back + V(0, 0, 0) - pr.get_world_location()
            p.set_actor_location(p.get_actor_location() + off, False, True)
            p.set_editor_property("Velocity", V(0, 0, 0)); p.set_editor_property("KThr", 0.0)
        elif stage == "locked":
            st["locking"] = True; st["tlock"] = now
            h.set_editor_property("TurbAmp", 0.0); h.set_editor_property("BowStrength", 0.0)
        st["tn"] = now + 2.5
    if st.get("locking"):
        # home on the basket mouth, then L
        aimp = d - fwd * 55.0; dv = aimp - pr.get_world_location(); Lh = max(dv.length(), 1.0)
        p.set_editor_property("Velocity", dv * (min(60.0, 2.0 * Lh) / Lh))
        if S == 2 and loc.x > -65 and r < 10 and now > st.get("tpress", 0): p.set_editor_property("LockCount", p.get_editor_property("LockCount") + 1); st["tpress"] = now + 0.5
        if S == 3:
            st["locking"] = False; st["tn"] = now + 2.0; p.set_editor_property("Velocity", V(0, 0, 0))
            h.set_editor_property("TurbAmp", 1.0); h.set_editor_property("BowStrength", 120.0)
        if now - st["tlock"] > 25:
            log("could not lock in 25 s - skipping"); st["locking"] = False; st["i"] = len(SHOTS); st["tn"] = now
        return
    if stage != "locked": p.set_editor_property("Velocity", V(0, 0, 0))
    # --- camera
    mir = p.get_actor_location()
    if mode == "cockpit":
        cam.set_relative_location(st["camrel"], False, True); cam.set_field_of_view(fov)
        rr = unreal.MathLibrary.find_look_at_rotation(cam.get_world_location(), d)
        p.set_editor_property("CamYaw", rr.yaw - 90.0); p.set_editor_property("CamPitch", rr.pitch + 4.0)
    elif mode == "hud":   # pilot eye, looking through the combiner (narrow FOV so the symbology is readable)
        cam.set_relative_location(st["camrel"], False, True); cam.set_field_of_view(fov)
        p.set_editor_property("CamYaw", 0.0); p.set_editor_property("CamPitch", -4.5)
    elif mode == "side":
        frame(p, cam, [pod, d, mir + V(0, -700, 0), mir + V(0, 600, 0)], V(-1.0, 0.12, 0.10), fov, 1.05)
    elif mode == "chase":
        aim(p, cam, mir + V(450.0, -1700.0, 380.0), d + V(0, 0, -60), fov)
    elif mode == "wide":
        if "tk" not in st: st["tk"] = tanker_points(w)
        frame(p, cam, st["tk"] + [mir + V(0, -700, 0), mir + V(0, 600, 0)], V(0.45, -0.75, 0.42), fov, 0.95)
    elif mode == "hose":
        pts = h.get_component_by_class(unreal.CableComponent).get_cable_particle_locations()
        q = pts[int(len(pts) * 0.8)] if pts else d + (pod - d) * 0.25
        aim(p, cam, q + V(-300.0, 60.0, 60.0), q, fov)
    elif mode == "close":
        aim(p, cam, d + V(-170.0, -70.0, 40.0), d + V(0, -45, 0), fov)
    if not st["shot"] and now > st["tn"]:
        log(name); unreal.SystemLibrary.execute_console_command(w, "HighResShot 2"); st["shot"] = True; st["tn"] = now + 2.0
    elif st["shot"] and now > st["tn"]:
        st["shot"] = False; st["i"] += 1; st["tn"] = now + 0.8
ONLY = [a for a in sys.argv[1:]]
if ONLY: SHOTS = [x for x in SHOTS if any(x[0].startswith(o) for o in ONLY)]
st["h"] = unreal.register_slate_post_tick_callback(tick)
