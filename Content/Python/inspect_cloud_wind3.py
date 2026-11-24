import unreal
log = lambda s: unreal.log("[CloudW2] " + s)
par = unreal.load_asset("/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud")
mel = unreal.MaterialEditingLibrary
exprs = list(mel.get_material_expressions(par))
by = {e.get_name(): e for e in exprs}
ins = {}
cons = {}
for e in exprs:
    try: srcs = [i.get_name() if i else "-" for i in mel.get_inputs_for_material_expression(par, e)]
    except Exception: srcs = []
    ins[e.get_name()] = srcs
    for s in srcs: cons.setdefault(s, []).append(e.get_name())
def d(n):
    e = by.get(n)
    if e is None: return n
    x = ""
    for p in ("parameter_name", "const_a", "const_b", "r", "g", "b", "a", "constant", "material_function", "period", "name"):
        try: x += " %s=%s" % (p, str(e.get_editor_property(p))[:80])
        except Exception: pass
    return "%s%s" % (n.replace("MaterialExpression", ""), x)
seen = set()
def down(n, depth):
    if depth > 7 or n in seen: return
    seen.add(n)
    for c in cons.get(n, []):
        log("  " * depth + "%s <- %s" % (d(c), [s.replace("MaterialExpression", "") for s in ins[c]]))
        down(c, depth + 1)
log("M26 <- %s" % [d(x) for x in ins.get("MaterialExpressionMultiply_26", [])])
for x in ins.get("MaterialExpressionMultiply_26", []):
    log("  %s <- %s" % (x, [d(y) for y in ins.get(x, [])]))
decl = by["MaterialExpressionNamedRerouteDeclaration_7"]
for e in exprs:
    if e.get_class().get_name() == "MaterialExpressionNamedRerouteUsage":
        try:
            if e.get_editor_property("declaration") == decl:
                log("== usage " + e.get_name()); down(e.get_name(), 1)
        except Exception as ex: log("err %s" % ex)
