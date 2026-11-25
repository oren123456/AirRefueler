// Runs the AARS link inside the game (PIE or packaged): one per game world.
//
// Blueprint use: Get World Subsystem "AarsLinkSubsystem", bind the On... events for what the Simulator sends,
// and write the World's side into WorldState (sent at WorldStateHz; seq, t_ms and clock are filled in here).
// C++ use: OnBeforeSendWorldState to fill WorldState right before it is sent; RestoreProvider / RestoreApplier for
// snapshot.request / world.set.
#pragma once

#include "CoreMinimal.h"
#include "AarsLinkServer.h"
#include "AarsTypes.h"
#include "Subsystems/WorldSubsystem.h"
#include "AarsLinkSubsystem.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE(FAarsLinkEvent);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FAarsHelloEvent, const FAarsHello&, Message);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FAarsPodHoseEvent, const FAarsPodHose&, Message);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FAarsPodFluidEvent, const FAarsPodFluid&, Message);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FAarsBoomDriveEvent, const FAarsBoomDrive&, Message);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FAarsBoomFluidEvent, const FAarsBoomFluid&, Message);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FAarsCameraLensEvent, const FAarsCameraLens&, Message);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FAarsClockSetEvent, const FAarsClockSet&, Message);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FAarsSnapshotRequestEvent, const FAarsSnapshotRequest&, Message);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FAarsWorldSetEvent, const FAarsWorldSet&, Message);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FAarsTankerSetEvent, const FAarsTankerSet&, Message);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FAarsReceiverAddEvent, const FAarsReceiverAdd&, Message);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FAarsReceiverCommandEvent, const FAarsReceiverCommand&, Message);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FAarsReceiverRemoveEvent, const FAarsReceiverRemove&, Message);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FAarsRejectedEvent, const FString&, Message, const FString&, Reason);

UCLASS()
class AARSLINK_API UAarsLinkSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	UAarsLinkSubsystem();
	virtual ~UAarsLinkSubsystem() override;

	// USubsystem / UWorldSubsystem
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;
	virtual void Deinitialize() override;
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;

	// FTickableGameObject
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override;
	virtual bool IsTickableWhenPaused() const override { return true; }

	/** The World's side, sent as world.state. Seq, TMs, ClockScale and bPaused are filled in when sending. */
	UPROPERTY(BlueprintReadWrite, Category = "AARS")
	FAarsWorldState WorldState;

	UPROPERTY(BlueprintAssignable, Category = "AARS") FAarsLinkEvent OnSimulatorConnected;
	UPROPERTY(BlueprintAssignable, Category = "AARS") FAarsLinkEvent OnSimulatorDisconnected;
	UPROPERTY(BlueprintAssignable, Category = "AARS") FAarsHelloEvent OnHello;
	UPROPERTY(BlueprintAssignable, Category = "AARS") FAarsPodHoseEvent OnPodHose;
	UPROPERTY(BlueprintAssignable, Category = "AARS") FAarsPodFluidEvent OnPodFluid;
	UPROPERTY(BlueprintAssignable, Category = "AARS") FAarsBoomDriveEvent OnBoomDrive;
	UPROPERTY(BlueprintAssignable, Category = "AARS") FAarsBoomFluidEvent OnBoomFluid;
	UPROPERTY(BlueprintAssignable, Category = "AARS") FAarsCameraLensEvent OnCameraLens;
	UPROPERTY(BlueprintAssignable, Category = "AARS") FAarsClockSetEvent OnClockSet;
	UPROPERTY(BlueprintAssignable, Category = "AARS") FAarsSnapshotRequestEvent OnSnapshotRequest;
	UPROPERTY(BlueprintAssignable, Category = "AARS") FAarsWorldSetEvent OnWorldSet;
	UPROPERTY(BlueprintAssignable, Category = "AARS") FAarsLinkEvent OnWorldResume;
	UPROPERTY(BlueprintAssignable, Category = "AARS") FAarsTankerSetEvent OnTankerSet;
	UPROPERTY(BlueprintAssignable, Category = "AARS") FAarsReceiverAddEvent OnReceiverAdd;
	UPROPERTY(BlueprintAssignable, Category = "AARS") FAarsReceiverCommandEvent OnReceiverCommand;
	UPROPERTY(BlueprintAssignable, Category = "AARS") FAarsReceiverRemoveEvent OnReceiverRemove;
	UPROPERTY(BlueprintAssignable, Category = "AARS") FAarsRejectedEvent OnRejected;

	UFUNCTION(BlueprintPure, Category = "AARS")
	bool IsSimulatorConnected() const;

	/** Last pod.hose received for a pod (false if none yet). */
	UFUNCTION(BlueprintPure, Category = "AARS")
	bool GetLastPodHose(EAarsPod Pod, FAarsPodHose& Out) const;

	/** Last boom.drive received (false if none yet). */
	UFUNCTION(BlueprintPure, Category = "AARS")
	bool GetLastBoomDrive(FAarsBoomDrive& Out) const;

	/** Answer a snapshot.request yourself (only needed when no RestoreProvider is set). */
	UFUNCTION(BlueprintCallable, Category = "AARS")
	void SendSnapshotReply(const FString& RequestId, const FString& RestoreJson);

	/** One line: port, Simulator, rates, last message. */
	UFUNCTION(BlueprintPure, Category = "AARS")
	FString GetStatusLine() const;

	/** World time in ms since BeginPlay (dilated, stops while paused) = world.state.t_ms. */
	int64 GetScenarioTimeMs() const;

	// ---- C++ hooks ----
	/** Fill WorldState right before each world.state. */
	TMulticastDelegate<void(FAarsWorldState&)> OnBeforeSendWorldState;
	/** Restore object for snapshot.request (JSON object text). If set, snapshot.reply is sent automatically. */
	TFunction<FString()> RestoreProvider;
	/** Apply a restore from world.set. Return false if not understood. */
	TFunction<bool(const FString&)> RestoreApplier;

private:
	void StartServer();
	void Note(const FString& Summary);

	TUniquePtr<FAarsLinkServer> Server;
	double StartWorldSeconds = 0.0;
	double SendAccumulator = 0.0;
	bool bHasPodHose[2] = { false, false };
	FAarsPodHose LastPodHose[2];
	bool bHasBoomDrive = false;
	FAarsBoomDrive LastBoomDrive;
	FString LastInbound;
	int32 ListenPort = 0;
	bool bChangedEditorThrottle = false;
	bool bSavedEditorThrottle = false;
	bool bListening = false;
	// rates
	double RateWindowStart = 0.0;
	int64 RxAtWindowStart = 0, TxAtWindowStart = 0;
	int32 RxPerSecond = 0, TxPerSecond = 0;
};
