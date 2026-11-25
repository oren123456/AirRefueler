using UnrealBuildTool;

public class AarsLink : ModuleRules
{
	public AarsLink(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine" });
		PrivateDependencyModuleNames.AddRange(new string[] { "Json", "WebSocketNetworking", "Sockets" });
	}
}
