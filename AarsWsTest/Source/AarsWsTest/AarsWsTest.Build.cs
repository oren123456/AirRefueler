using System.IO;
using UnrealBuildTool;

public class AarsWsTest : ModuleRules
{
	// Set to false if the private-header socket probe does not compile.
	static readonly bool bFdProbe = true;

	public AarsWsTest(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PrivateDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", "Json", "WebSocketNetworking", "Sockets", "AarsLink" });

		if (bFdProbe)
		{
			// Test-only: reach FWebSocket::Wsi to read TCP_NODELAY from the real socket.
			string Eng = Path.GetFullPath(EngineDirectory);
			PrivateIncludePaths.Add(Path.Combine(Eng, "Plugins", "Experimental", "WebSocketNetworking", "Source", "WebSocketNetworking", "Private"));
			PrivateIncludePaths.Add(Path.Combine(Eng, "Source"));
			PrivateIncludePaths.Add(Path.Combine(Eng, "Source", "Runtime", "Sockets", "Private"));
			PrivateDependencyModuleNames.AddRange(new string[] { "libWebSockets", "OpenSSL", "zlib" });
			PrivateDefinitions.Add("WITH_FD_PROBE=1");
		}
		else
		{
			PrivateDefinitions.Add("WITH_FD_PROBE=0");
		}
	}
}
