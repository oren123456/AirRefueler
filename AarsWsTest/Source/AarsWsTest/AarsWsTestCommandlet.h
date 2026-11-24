#pragma once

#include "Commandlets/Commandlet.h"
#include "AarsWsTestCommandlet.generated.h"

/**
 * Throwaway WebSocketNetworking test server for the AARS <-> World link.
 * UnrealEditor-Cmd.exe AarsWsTest.uproject -run=AarsWsTest -port=8765 -mode=stream -pre=1 -post=0 -seconds=20 -out=<json> -ready=<file>
 *  mode=stream : send a world.state (~800 B) every frame
 *  mode=nagle  : no stream; every 0.5 s send two small messages (A then B) in back-to-back Ticks
 *  pre/post    : Server->Tick() calls before / after the frame's Send
 */
UCLASS()
class UAarsWsTestCommandlet : public UCommandlet
{
	GENERATED_BODY()

public:
	UAarsWsTestCommandlet();
	virtual int32 Main(const FString& Params) override;
};
