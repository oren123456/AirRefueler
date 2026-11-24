"""Keep the editor/PIE at full frame rate when the window is not in the foreground (needed for remote PIE tests)."""
import unreal
cls = unreal.load_class(None, "/Script/UnrealEd.EditorPerformanceSettings")
s = unreal.get_default_object(cls)
for n in ("bThrottleCPUWhenNotForeground", "throttle_cpu_when_not_foreground"):
    try:
        unreal.log("[NoThrottle] before %s=%s" % (n, s.get_editor_property(n)))
        s.set_editor_property(n, False)
        unreal.log("[NoThrottle] %s=%s" % (n, s.get_editor_property(n)))
        break
    except Exception as e:
        unreal.log("[NoThrottle] %s: %s" % (n, e))
