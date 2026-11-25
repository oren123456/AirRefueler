"""Unregister leftover slate post-tick callbacks from test scripts (argv: marker text in the callback's log prefix)
and stop PIE."""
import unreal, gc, sys
marker = sys.argv[1] if len(sys.argv) > 1 else "[LockShot]"
n = 0
for f in gc.get_objects():
    try:
        if callable(f) and getattr(f, "__name__", "") == "tick" and hasattr(f, "__globals__"):
            g = f.__globals__
            src = " ".join(str(c) for c in f.__code__.co_consts) + str(g.get("log", ""))
            stv = g.get("st")
            lg = g.get("log")
            consts = " ".join(str(c) for c in getattr(getattr(lg, "__code__", None), "co_consts", ()))
            if isinstance(stv, dict) and stv.get("h") is not None and (marker in consts or marker in src):
                unreal.unregister_slate_post_tick_callback(stv["h"]); stv["h"] = None; n += 1
    except Exception:
        pass
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
unreal.log("[Unhook] removed %d callback(s) for %s" % (n, marker))
