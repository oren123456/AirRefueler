import unreal
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
A = unreal.Vector(-1720.31, -4560.91, 241.27); B = unreal.Vector(-1720.54, -4557.29, 254.39); C = unreal.Vector(-1734.33, -4560.87, 241.02)
ex = (C - A).normal(); ey = (B - A); ey = (ey - ex * ey.dot(ex)).normal(); n = ex.cross(ey)
if n.y > 0: n = -n
res = []
for t in [6.0, 7.0, 8.0, 9.0, 10.0]:
    row = []
    for s in [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0]:
        p = A + ex * s + ey * t
        hit = unreal.SystemLibrary.line_trace_single(w, p + n * 8.0, p - n * 1.0, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [], unreal.DrawDebugTrace.NONE, True)
        if hit is None: row.append("-"); continue
        tup = hit.to_tuple()
        loc = tup[4]; comp = tup[9]
        h = (loc - A).dot(n)
        row.append("%s:%.1f" % (comp.get_owner().get_actor_label()[:3] if comp else "?", h))
    res.append("t=%g " % t + " ".join(row))
unreal.log("[UfcpTrace] " + " || ".join(res))
