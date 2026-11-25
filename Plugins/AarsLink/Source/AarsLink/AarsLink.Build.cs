using UnrealBuildTool;

public class AarsLink : ModuleRules
{
	public AarsLink(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine" });
		PrivateDependencyModuleNames.AddRange(new string[] { "Json", "WebSocketNetworking", "Sockets" });
		PublicDependencyModuleNames.Add("DeveloperSettings");
		if (Target.bBuildEditor)
		{
			PrivateDependencyModuleNames.Add("UnrealEd"); // keep the editor running at full rate while PIE serves the Simulator
		}
	}
}
