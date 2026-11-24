import unreal
log = lambda s: unreal.log("[CloudGraph] " + s)
par = unreal.load_asset("/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud")
mel = unreal.MaterialEditingLibrary
exprs = []
for fn in ("get_material_expressions",):
    if hasattr(mel, fn):
        exprs = list(getattr(mel, fn)(par)); log("via %s %d" % (fn, len(exprs)))
if not exprs:
    try:
        eod = par.get_editor_property("editor_only_data")
        coll = eod.get_editor_property("expression_collection")
        exprs = list(coll.get_editor_property("expressions")); log("via collection %d" % len(exprs))
    except Exception as e:
        log("collection fail %s" % e)
byname = {e.get_name(): e for e in exprs}
def desc(e):
    n = e.get_class().get_name()
    extra = ""
    for p in ("parameter_name", "code", "input_name", "const_a", "const_b", "r", "constant", "function_name"):
        try: extra += " %s=%s" % (p, str(e.get_editor_property(p))[:300])
        except Exception: pass
    return "%s %s%s" % (e.get_name(), n, extra)
wind = [e for e in exprs if "Wind" in str(getattr(e, "get_editor_property") and (lambda: e.get_editor_property("parameter_name"))() if hasattr(e, "parameter_name") or True else "")] if False else []
for e in exprs:
    try:
        pn = str(e.get_editor_property("parameter_name"))
    except Exception:
        pn = ""
    if "Wind" in pn or "Placement" in pn or e.get_class().get_name() in ("MaterialExpressionTime", "MaterialExpressionCustom"):
        log("P " + desc(e))
# who consumes what: walk all expressions, list inputs that reference wind/time
for e in exprs:
    try:
        ins = mel.get_inputs_for_material_expression(par, e)
    except Exception:
        continue
    srcs = [i.get_name() if i else "-" for i in ins]
    if any(("Parameter" in s or "Time" in s) for s in srcs):
        log("E %s <- %s" % (desc(e)[:200], srcs))
