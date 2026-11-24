"""Flight illusion: stream the volumetric cloud deck backward past the static formation.
Aircraft noses point +Y, so the clouds must travel -Y. In m_SimpleVolumetricCloud a +Y wind moves the
cloud pattern toward -Y. Calibrated (top-down shots 4 s apart, CloudGlobalScale 220): wind 1.0 ~= 375 m/s.
argv: ground speed in m/s (default 160 ~ 310 kt TAS, typical probe-and-drogue refuelling speed)."""
import unreal, sys
MPS_PER_UNIT = 375.0
v = float(sys.argv[1]) if len(sys.argv) > 1 else 160.0
w = v / MPS_PER_UNIT
mel = unreal.MaterialEditingLibrary
mi = unreal.load_asset("/Game/AirRefueler/Maps/MI_VolumetricCloud_Refuel")
# small Z component keeps the cloud tops slowly billowing instead of sliding like a rigid texture
mel.set_material_instance_vector_parameter_value(mi, "Layout_WindControls", unreal.LinearColor(0.0, w, 0.04, 1.0))
mel.update_material_instance(mi)
unreal.EditorAssetLibrary.save_loaded_asset(mi)
unreal.log("[CloudFlight] %.0f m/s -> Layout_WindControls=(0, %.3f, 0.04, 1)" % (v, w))
