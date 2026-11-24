using UnrealBuildTool;

public class AarsWsTestTarget : TargetRules
{
	public AarsWsTestTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("AarsWsTest");
	}
}
