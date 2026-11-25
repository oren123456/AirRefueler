using UnrealBuildTool;

public class AirRefuelerEditorTarget : TargetRules
{
	public AirRefuelerEditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("AirRefueler");
	}
}
