using UnrealBuildTool;

public class AirRefuelerTarget : TargetRules
{
	public AirRefuelerTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("AirRefueler");
	}
}
