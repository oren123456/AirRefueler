#include "AarsLinkSubsystem.h"

#include "AarsCodec.h"
#include "AarsLinkLog.h"
#include "AarsLinkServer.h"
#include "AarsLinkSettings.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "GameFramework/WorldSettings.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/App.h"
#if WITH_EDITOR
#include "Editor/EditorPerformanceSettings.h"
#endif

UAarsLinkSubsystem::UAarsLinkSubsystem() = default;
UAarsLinkSubsystem::~UAarsLinkSubsystem() = default;

bool UAarsLinkSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

void UAarsLinkSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);
	const UAarsLinkSettings* S = GetDefault<UAarsLinkSettings>();
	WorldState.Tanker = S->DefaultTanker;
	StartWorldSeconds = InWorld.GetTimeSeconds();
	if (S->bEnabled) StartServer();
#if WITH_EDITOR
	if (S->bEnabled && S->bKeepEditorRunningInBackground && GIsEditor && InWorld.WorldType == EWorldType::PIE)
	{
		UEditorPerformanceSettings* Perf = GetMutableDefault<UEditorPerformanceSettings>();
		bSavedEditorThrottle = Perf->bThrottleCPUWhenNotForeground;
		Perf->bThrottleCPUWhenNotForeground = false;
		bChangedEditorThrottle = true;
	}
#endif
}

void UAarsLinkSubsystem::Deinitialize()
{
#if WITH_EDITOR
	if (bChangedEditorThrottle)
	{
		GetMutableDefault<UEditorPerformanceSettings>()->bThrottleCPUWhenNotForeground = bSavedEditorThrottle;
		bChangedEditorThrottle = false;
	}
#endif
	Server.Reset();
	bListening = false;
	Super::Deinitialize();
}

int64 UAarsLinkSubsystem::GetScenarioTimeMs() const
{
	const UWorld* W = GetWorld();
	return W ? (int64)FMath::Max(0.0, (W->GetTimeSeconds() - StartWorldSeconds) * 1000.0) : 0;
}

bool UAarsLinkSubsystem::IsSimulatorConnected() const
{
	return Server && Server->IsConnected();
}

bool UAarsLinkSubsystem::GetLastPodHose(EAarsPod Pod, FAarsPodHose& Out) const
{
	const int32 I = (int32)Pod;
	if (I < 0 || I > 1 || !bHasPodHose[I]) return false;
	Out = LastPodHose[I];
	return true;
}

bool UAarsLinkSubsystem::GetLastBoomDrive(FAarsBoomDrive& Out) const
{
	if (!bHasBoomDrive) return false;
	Out = LastBoomDrive;
	return true;
}

void UAarsLinkSubsystem::SendSnapshotReply(const FString& RequestId, const FString& RestoreJson)
{
	if (Server) Server->SendSnapshotReply(RequestId, GetScenarioTimeMs(), RestoreJson);
}

void UAarsLinkSubsystem::Note(const FString& Summary)
{
	LastInbound = Summary;
}

void UAarsLinkSubsystem::StartServer()
{
	const UAarsLinkSettings* S = GetDefault<UAarsLinkSettings>();
	ListenPort = S->Port;
	Server = MakeUnique<FAarsLinkServer>();
	FAarsLinkServer& L = *Server;
	const FString Yes = TEXT("yes"), No = TEXT("no");

	L.OnConnected.AddLambda([this]() { Note(TEXT("Simulator connected")); OnSimulatorConnected.Broadcast(); });
	L.OnDisconnected.AddLambda([this]() { Note(TEXT("Simulator disconnected")); OnSimulatorDisconnected.Broadcast(); });
	L.OnHello.AddLambda([this](const FAarsHello& M) { Note(FString::Printf(TEXT("hello %s %s"), *M.Name, *M.Version)); OnHello.Broadcast(M); });
	L.OnPing.AddLambda([this](const FAarsPing& M) { Note(FString::Printf(TEXT("ping %s"), *M.Id)); });
	L.OnPodHose.AddLambda([this, Yes, No](const FAarsPodHose& M)
	{
		LastPodHose[(int32)M.Pod] = M;
		bHasPodHose[(int32)M.Pod] = true;
		Note(FString::Printf(TEXT("pod.hose %s payout %.1f ft, attached %s, cut %s"), AarsCodec::ToString(M.Pod), M.PayoutFt, M.bAttached ? *Yes : *No, M.bCut ? *Yes : *No));
		OnPodHose.Broadcast(M);
	});
	L.OnPodFluid.AddLambda([this](const FAarsPodFluid& M)
	{
		Note(FString::Printf(TEXT("pod.fluid %s %.0f psi %.0f lb/min"), AarsCodec::ToString(M.Pod), M.FuelPressurePsi, M.FlowLbMin));
		OnPodFluid.Broadcast(M);
	});
	L.OnBoomDrive.AddLambda([this, Yes, No](const FAarsBoomDrive& M)
	{
		LastBoomDrive = M;
		bHasBoomDrive = true;
		Note(FString::Printf(TEXT("boom.drive el %.1f az %.1f tele %.1f ft, attached %s"), M.ElDeg, M.AzDeg, M.TeleFt, M.bAttached ? *Yes : *No));
		OnBoomDrive.Broadcast(M);
	});
	L.OnBoomFluid.AddLambda([this](const FAarsBoomFluid& M)
	{
		Note(FString::Printf(TEXT("boom.fluid %.0f psi %.0f lb/min"), M.FuelPressurePsi, M.FlowLbMin));
		OnBoomFluid.Broadcast(M);
	});
	L.OnCameraLens.AddLambda([this](const FAarsCameraLens& M)
	{
		Note(FString::Printf(TEXT("camera.lens %s %s"), AarsCodec::ToString(M.Pod), AarsCodec::ToString(M.Lens)));
		OnCameraLens.Broadcast(M);
	});
	L.OnCameraSelect.AddLambda([this](const FAarsCameraSelect& M)
	{
		Note(FString::Printf(TEXT("camera.select %s"), AarsCodec::ToString(M.Pod)));
		OnCameraSelect.Broadcast(M);
	});
	L.OnClockSet.AddLambda([this](const FAarsClockSet& M)
	{
		Note(FString::Printf(TEXT("clock.set scale %g%s"), M.Scale, M.bPaused ? TEXT(", paused") : TEXT("")));
		if (GetDefault<UAarsLinkSettings>()->bApplyClockSet)
		{
			if (UWorld* W = GetWorld())
			{
				if (AWorldSettings* WS = W->GetWorldSettings())
				{
					WS->MaxGlobalTimeDilation = FMath::Max(WS->MaxGlobalTimeDilation, 100.0f);
				}
				UGameplayStatics::SetGlobalTimeDilation(W, (float)M.Scale);
				UGameplayStatics::SetGamePaused(W, M.bPaused);
			}
		}
		OnClockSet.Broadcast(M);
	});
	L.OnSnapshotRequest.AddLambda([this](const FAarsSnapshotRequest& M)
	{
		Note(FString::Printf(TEXT("snapshot.request %s"), *M.RequestId));
		if (RestoreProvider)
		{
			SendSnapshotReply(M.RequestId, RestoreProvider());
		}
		else if (!OnSnapshotRequest.IsBound())
		{
			UE_LOG(LogAarsLink, Warning, TEXT("AARS link: snapshot.request with no restore provider: replying with an empty restore"));
			SendSnapshotReply(M.RequestId, TEXT("{}"));
		}
		OnSnapshotRequest.Broadcast(M);
	});
	L.OnWorldSet.AddLambda([this](const FAarsWorldSet& M)
	{
		const bool bOk = RestoreApplier ? RestoreApplier(M.RestoreJson) : false;
		Note(FString::Printf(TEXT("world.set t_ms %lld%s"), M.TMs, bOk ? TEXT("") : TEXT(" (restore not applied)")));
		OnWorldSet.Broadcast(M);
	});
	L.OnWorldResume.AddLambda([this]() { Note(TEXT("world.resume")); OnWorldResume.Broadcast(); });
	L.OnTankerSet.AddLambda([this](const FAarsTankerSet& M)
	{
		if (M.bHasIasKt) WorldState.Tanker.IasKt = M.IasKt;
		if (M.bHasAltFt) WorldState.Tanker.AltFt = M.AltFt;
		if (M.bHasBankDeg) WorldState.Tanker.BankDeg = M.BankDeg;
		if (M.bHasAp) WorldState.Tanker.Ap = M.Ap;
		Note(TEXT("tanker.set"));
		OnTankerSet.Broadcast(M);
	});
	L.OnReceiverAdd.AddLambda([this](const FAarsReceiverAdd& M)
	{
		Note(FString::Printf(TEXT("receiver.add %s %s behind %s"), *M.Id, AarsCodec::ToString(M.ReceiverType), AarsCodec::ToString(M.Behind)));
		OnReceiverAdd.Broadcast(M);
	});
	L.OnReceiverCommand.AddLambda([this](const FAarsReceiverCommand& M)
	{
		Note(FString::Printf(TEXT("receiver.command %s %s"), *M.Id, AarsCodec::ToString(M.Action)));
		OnReceiverCommand.Broadcast(M);
	});
	L.OnReceiverRemove.AddLambda([this](const FAarsReceiverRemove& M)
	{
		Note(FString::Printf(TEXT("receiver.remove %s"), *M.Id));
		OnReceiverRemove.Broadcast(M);
	});
	L.OnRejected.AddLambda([this](const FString& Raw, const FString& Why)
	{
		Note(TEXT("REJECTED: ") + Why);
		OnRejected.Broadcast(Raw, Why);
	});

	bListening = L.Start(S->Port, S->BindAddress, S->WorldName);
	if (!bListening) Server.Reset();
	RateWindowStart = FPlatformTime::Seconds();
}

void UAarsLinkSubsystem::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	const UAarsLinkSettings* S = GetDefault<UAarsLinkSettings>();

	if (Server)
	{
		Server->Receive();

		SendAccumulator += FApp::GetDeltaTime(); // real time: the stream stays at WorldStateHz when the game is slowed or paused
		const double Period = 1.0 / FMath::Max(1, S->WorldStateHz);
		if (SendAccumulator >= Period * 0.98)
		{
			SendAccumulator = FMath::Min(SendAccumulator - Period, Period);
			UWorld* W = GetWorld();
			WorldState.TMs = GetScenarioTimeMs();
			if (W)
			{
				WorldState.bPaused = W->IsPaused();
				const AWorldSettings* WS = W->GetWorldSettings();
				WorldState.ClockScale = WS ? WS->GetEffectiveTimeDilation() : 1.0;
			}
			OnBeforeSendWorldState.Broadcast(WorldState);
			if (Server->IsConnected()) Server->SendWorldState(WorldState);
		}
		Server->Flush();

		const double Now = FPlatformTime::Seconds();
		if (Now - RateWindowStart >= 1.0)
		{
			const FAarsLinkServer::FStats& St = Server->GetStats();
			RxPerSecond = (int32)((St.Received - RxAtWindowStart) / (Now - RateWindowStart));
			TxPerSecond = (int32)((St.Sent - TxAtWindowStart) / (Now - RateWindowStart));
			RxAtWindowStart = St.Received;
			TxAtWindowStart = St.Sent;
			RateWindowStart = Now;
		}
	}

	if (S->bShowStatusOnScreen && S->bEnabled && GEngine)
	{
		const FColor Color = !bListening ? FColor::Red : (IsSimulatorConnected() ? FColor::Green : FColor(255, 170, 0));
		GEngine->AddOnScreenDebugMessage((uint64)0xAA250001, 0.5f, Color, GetStatusLine());
	}
}

FString UAarsLinkSubsystem::GetStatusLine() const
{
	if (!bListening)
	{
		return FString::Printf(TEXT("AARS link: NOT running - port %d is busy or invalid (Project Settings > Plugins > AARS Link, see Output Log)"), ListenPort);
	}
	if (!Server->IsConnected())
	{
		return FString::Printf(TEXT("AARS link :%d - waiting for the Simulator%s"), ListenPort,
			LastInbound.IsEmpty() ? TEXT("") : *(TEXT("  |  last: ") + LastInbound));
	}
	const FAarsLinkServer::FStats& St = Server->GetStats();
	FString Peer = St.PeerName.IsEmpty() ? FString(TEXT("Simulator")) : FString::Printf(TEXT("'%s' %s"), *St.PeerName, *St.PeerVersion);
	if (St.bVersionMismatch) Peer += TEXT(" (WRONG CONTRACT VERSION - ignored)");
	return FString::Printf(TEXT("AARS link :%d - %s connected  |  in %d/s  out %d/s  rejected %lld  |  last: %s"),
		ListenPort, *Peer, RxPerSecond, TxPerSecond, St.Rejected, *LastInbound);
}

TStatId UAarsLinkSubsystem::GetStatId() const
{
	RETURN_QUICK_DECLARE_CYCLE_STAT(UAarsLinkSubsystem, STATGROUP_Tickables);
}
