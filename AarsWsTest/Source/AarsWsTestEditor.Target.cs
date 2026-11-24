using UnrealBuildTool;

public class AarsWsTestEditorTarget : TargetRules
{
	public AarsWsTestEditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("AarsWsTest");
	}
}
