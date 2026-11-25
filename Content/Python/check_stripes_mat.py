import unreal
mel = unreal.MaterialEditingLibrary
m = unreal.load_asset("/Game/AirRefueler/Sim/Materials/M_HoseStripes")
log = lambda s: unreal.log("[StripeMat] " + s)
log("expressions=%d" % mel.get_num_material_expressions(m))
bc = mel.get_material_property_input_node(m, unreal.MaterialProperty.MP_BASE_COLOR)
log("basecolor <- %s" % (bc.get_name() if bc else None))
if bc:
    log("lerp inputs %s" % [i.get_name() if i else None for i in mel.get_inputs_for_material_expression(m, bc)])
for e in mel.get_material_expressions(m):
    ins = [i.get_name() if i else None for i in mel.get_inputs_for_material_expression(m, e)]
    log("%s <- %s" % (e.get_name(), ins))
