#pragma once

#include "CoreMinimal.h"
#include "AarsTypes.h"
#include "Engine/DeveloperSettings.h"
#include "AarsLinkSettings.generated.h"

/** Project Settings > Plugins > AARS Link (saved in Config/DefaultGame.ini). */
UCLASS(config = Game, defaultconfig, meta = (DisplayName = "AARS Link"))
class AARSLINK_API UAarsLinkSettings : public UDeveloperSettings
{
	GENERATED_BODY()

public:
	UAarsLinkSettings();
	virtual FName GetCategoryName() const override { return TEXT("Plugins"); }

	/** Run the AARS link server while the game runs (PIE or packaged game). */
	UPROPERTY(Config, EditAnywhere, Category = "Server")
	bool bEnabled = true;

	/** Port the World listens on; the Simulator connects to it. The contract leaves the port to be agreed. */
	UPROPERTY(Config, EditAnywhere, Category = "Server", meta = (ClampMin = 1, ClampMax = 65535))
	int32 Port = 9100;

	/** Empty = all network interfaces (the Simulator runs on another PC). 127.0.0.1 = this PC only. */
	UPROPERTY(Config, EditAnywhere, Category = "Server")
	FString BindAddress;

	/** hello.name the World sends. */
	UPROPERTY(Config, EditAnywhere, Category = "Server")
	FString WorldName = TEXT("AirRefueler");

	/** world.state rate (contract: 60 Hz). */
	UPROPERTY(Config, EditAnywhere, Category = "Server", meta = (ClampMin = 1, ClampMax = 240))
	int32 WorldStateHz = 60;

	/** clock.set changes the game's time dilation and pause (the contract requires the World to support it). */
	UPROPERTY(Config, EditAnywhere, Category = "World")
	bool bApplyClockSet = true;

	/** Tanker values used until the game sets its own (the AirRefueler tanker does not fly). */
	UPROPERTY(Config, EditAnywhere, Category = "World")
	FAarsTanker DefaultTanker;

	/**
	 * While playing in the editor, turn off "Use Less CPU when in Background" so the World keeps 60 Hz when another window
	 * (e.g. the Simulator or the test console) has the focus. Restored when play stops.
	 */
	UPROPERTY(Config, EditAnywhere, Category = "Server")
	bool bKeepEditorRunningInBackground = true;

	/** Link status and the last message received, on screen while playing. */
	UPROPERTY(Config, EditAnywhere, Category = "Debug")
	bool bShowStatusOnScreen = true;
};
