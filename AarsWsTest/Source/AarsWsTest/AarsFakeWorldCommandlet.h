#pragma once

#include "Commandlets/Commandlet.h"
#include "AarsFakeWorldCommandlet.generated.h"

/**
 * A stand-in World that speaks the whole AARS contract 0.2 through the AarsLink plugin, with no 3D scene:
 * it follows pod.hose / boom.drive, runs the demonstrator commands, the clock, snapshots and replay, and sends
 * world.state at 60 Hz. For testing a Simulator (or this link) without the AirRefueler game.
 *
 * UnrealEditor-Cmd.exe AarsWsTest.uproject -run=AarsFakeWorld [-port=8765] [-bind=0.0.0.0] [-seconds=0] [-restore]
 *   -bind     default: all interfaces            -seconds  0 = run until Ctrl+C
 *   -restore  carry restore in every 2nd world.state (30 Hz, as the contract suggests for recording)
 *   -out=<json> -ready=<file> -allowquit  (used by Tools/run_tests.py)
 */
UCLASS()
class UAarsFakeWorldCommandlet : public UCommandlet
{
	GENERATED_BODY()

public:
	UAarsFakeWorldCommandlet();
	virtual int32 Main(const FString& Params) override;
};
