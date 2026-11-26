#include "AirRefuelerAarsBridge.h"

#include "AarsLinkSubsystem.h"
#include "CineCameraActor.h"
#include "CineCameraComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/SceneCapture2D.h"
#include "Engine/TextureRenderTarget2D.h"
#include "IPixelStreaming2Module.h"
#include "IPixelStreaming2Streamer.h"
#include "PixelStreaming2VideoProducers.h"
#include "RenderingThread.h"
#include "Engine/Engine.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "InputCoreTypes.h"
#include "Components/SceneComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"
#include "Policies/CondensedJsonPrintPolicy.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

namespace
{
	constexpr double CmPerFt = 30.48;
	constexpr double CmPerSecPerKt = 51.4444;
	const TCHAR* PlayerId = TEXT("PLAYER");

	// Blueprint variables by name (BP_RefuelHose: State, HoseLen, Fuel, Parachute; BP_MiragePawn: ProbeTip, Velocity).
	bool GetInt(const UObject* O, FName Name, int32& Out)
	{
		if (!O) return false;
		if (const FIntProperty* P = FindFProperty<FIntProperty>(O->GetClass(), Name)) { Out = P->GetPropertyValue_InContainer(O); return true; }
		return false;
	}
	bool SetInt(UObject* O, FName Name, int32 V)
	{
		if (!O) return false;
		if (const FIntProperty* P = FindFProperty<FIntProperty>(O->GetClass(), Name)) { P->SetPropertyValue_InContainer(O, V); return true; }
		return false;
	}
	bool GetReal(const UObject* O, FName Name, double& Out)
	{
		if (!O) return false;
		if (const FDoubleProperty* P = FindFProperty<FDoubleProperty>(O->GetClass(), Name)) { Out = P->GetPropertyValue_InContainer(O); return true; }
		if (const FFloatProperty* P = FindFProperty<FFloatProperty>(O->GetClass(), Name)) { Out = P->GetPropertyValue_InContainer(O); return true; }
		return false;
	}
	bool SetBool(UObject* O, FName Name, bool V)
	{
		if (!O) return false;
		if (const FBoolProperty* P = FindFProperty<FBoolProperty>(O->GetClass(), Name)) { P->SetPropertyValue_InContainer(O, V); return true; }
		return false;
	}
	bool SetString(UObject* O, FName Name, const FString& V)
	{
		if (!O) return false;
		if (const FStrProperty* P = FindFProperty<FStrProperty>(O->GetClass(), Name)) { P->SetPropertyValue_InContainer(O, V); return true; }
		return false;
	}
	bool SetReal(UObject* O, FName Name, double V)
	{
		if (!O) return false;
		if (const FDoubleProperty* P = FindFProperty<FDoubleProperty>(O->GetClass(), Name)) { P->SetPropertyValue_InContainer(O, V); return true; }
		if (const FFloatProperty* P = FindFProperty<FFloatProperty>(O->GetClass(), Name)) { P->SetPropertyValue_InContainer(O, (float)V); return true; }
		return false;
	}
	bool GetVector(const UObject* O, FName Name, FVector& Out)
	{
		if (!O) return false;
		const FStructProperty* P = FindFProperty<FStructProperty>(O->GetClass(), Name);
		if (!P || P->Struct != TBaseStructure<FVector>::Get()) return false;
		Out = *P->ContainerPtrToValuePtr<FVector>(O);
		return true;
	}
	bool SetVector(UObject* O, FName Name, const FVector& V)
	{
		if (!O) return false;
		const FStructProperty* P = FindFProperty<FStructProperty>(O->GetClass(), Name);
		if (!P || P->Struct != TBaseStructure<FVector>::Get()) return false;
		*P->ContainerPtrToValuePtr<FVector>(O) = V;
		return true;
	}
	USceneComponent* GetComponent(const UObject* O, FName Name)
	{
		if (!O) return nullptr;
		if (const FObjectProperty* P = FindFProperty<FObjectProperty>(O->GetClass(), Name))
		{
			return Cast<USceneComponent>(P->GetObjectPropertyValue_InContainer(O));
		}
		return nullptr;
	}

	TArray<TSharedPtr<FJsonValue>> Arr(const FVector& V)
	{
		return { MakeShared<FJsonValueNumber>(V.X), MakeShared<FJsonValueNumber>(V.Y), MakeShared<FJsonValueNumber>(V.Z) };
	}
	bool ReadArr(const TSharedPtr<FJsonObject>& O, const TCHAR* K, FVector& Out)
	{
		const TArray<TSharedPtr<FJsonValue>>* A;
		if (!O->TryGetArrayField(K, A) || A->Num() != 3) return false;
		Out = FVector((*A)[0]->AsNumber(), (*A)[1]->AsNumber(), (*A)[2]->AsNumber());
		return true;
	}
}

bool UAirRefuelerAarsBridge::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

void UAirRefuelerAarsBridge::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);
	UAarsLinkSubsystem* L = InWorld.GetSubsystem<UAarsLinkSubsystem>();
	if (!L) return;
	Link = L;
	FindHoses();
	SetupPodCameras();
	SetupStream();
	L->OnCameraLens.AddDynamic(this, &UAirRefuelerAarsBridge::HandleCameraLens);
	L->OnCameraSelect.AddDynamic(this, &UAirRefuelerAarsBridge::HandleCameraSelect);
	L->OnBeforeSendWorldState.AddUObject(this, &UAirRefuelerAarsBridge::FillWorldState);
	TWeakObjectPtr<UAirRefuelerAarsBridge> Weak(this);
	L->RestoreProvider = [Weak]() { return Weak.IsValid() ? Weak->MakeRestore() : FString(TEXT("{}")); };
	L->RestoreApplier = [Weak](const FString& Json) { return Weak.IsValid() && Weak->ApplyRestore(Json); };
}

TStatId UAirRefuelerAarsBridge::GetStatId() const
{
	RETURN_QUICK_DECLARE_CYCLE_STAT(UAirRefuelerAarsBridge, STATGROUP_Tickables);
}

// Runs after the actors' Tick (tickable objects tick at the end of the world tick), so it corrects what
// BP_RefuelHose did this frame and the Blueprint draws from it next frame.
void UAirRefuelerAarsBridge::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	PollKeys();
	FeedStreamer();
	UAarsLinkSubsystem* L = Link.Get();
	if (!L) return;
	for (FHose& H : Hoses)
	{
		FAarsPodHose M;
		if (L->GetLastPodHose(H.Pod, M)) DriveHose(H, M);
	}
}

void UAirRefuelerAarsBridge::DriveHose(FHose& H, const FAarsPodHose& M)
{
	AActor* A = H.Actor.Get();
	if (!A) return;
	UWorld* W = GetWorld();
	const double Now = W ? W->GetTimeSeconds() : 0.0;

	if (!H.bSimControlled)
	{
		H.bSimControlled = true;
		SetString(A, TEXT("Msg"), TEXT("Hose under Simulator control (pod.hose)"));
	}
	if (H.bCut) return;
	if (M.bCut)
	{
		// Contract: once cut, hose and drogue are separated from the pod for good.
		H.bCut = true;
		if (USceneComponent* Hose = GetComponent(A, TEXT("Hose"))) Hose->SetVisibility(false, true);
		if (USceneComponent* Drogue = GetComponent(A, TEXT("Parachute"))) Drogue->SetVisibility(false, true);
		SetBool(A, TEXT("Flowing"), false);
		SetInt(A, TEXT("State"), 5); // no BP branch handles 5: hose frozen, all pod lights off
		SetString(A, TEXT("Msg"), TEXT("HOSE CUT (Simulator)"));
		return;
	}

	const double PayoutCm = FMath::Max(0.0, M.PayoutFt) * CmPerFt;
	const double FullCm = FullHoseFt * CmPerFt;
	const double LimitCm = M.bAttached ? FullCm : PayoutCm;
	// BP_RefuelHose measures push-in from FullLen (fuel window, "backed out" check)
	SetReal(A, TEXT("FullLen"), FMath::Max(1.0, LimitCm));

	if (M.Seq != H.LastSeq)
	{
		if (H.LastPayoutFt >= 0.0 && FMath::Abs(M.PayoutFt - H.LastPayoutFt) > 0.01)
		{
			H.bExtending = M.PayoutFt > H.LastPayoutFt;
			H.LastChangeTime = Now;
		}
		H.LastPayoutFt = M.PayoutFt;
		H.LastSeq = M.Seq;
	}

	int32 State = 0;
	GetInt(A, TEXT("State"), State);

	if (State == 3)
	{
		// Latched: the hose length is the probe's distance (BP sets HoseLen = d). Without "attached" the drum does not
		// give more than the payout; with it, up to the full length. Past the limit + 1 ft the probe pulls out.
		double D = 0.0;
		GetReal(A, TEXT("HoseLen"), D);
		if (D > LimitCm + DisconnectMarginFt * CmPerFt)
		{
			SetInt(A, TEXT("State"), 2);
			SetBool(A, TEXT("Flowing"), false);
			SetReal(A, TEXT("KO"), Now + 1.5);
			SetString(A, TEXT("Msg"), M.bAttached ? TEXT("Disconnected - past the full hose length")
			                                      : TEXT("Disconnected - the drum did not pay out more hose (not attached)"));
		}
		return;
	}

	if (PayoutCm < 1.0)
	{
		SetInt(A, TEXT("State"), 0); // BP draws the drogue into the pod tunnel
		return;
	}
	const bool bMoving = Now - H.LastChangeTime < 0.3;
	SetReal(A, TEXT("HoseLen"), PayoutCm);
	// 1 = trailing (red), 4 = rewinding (red), 2 = ready (amber). State 1 is not used at >= 24 m: the BP would clamp
	// HoseLen to its own 24 m end stop for a frame.
	int32 NewState = 2;
	if (bMoving) NewState = H.bExtending ? (PayoutCm < 2390.0 ? 1 : 2) : 4;
	SetInt(A, TEXT("State"), NewState);
}

void UAirRefuelerAarsBridge::FindHoses()
{
	Hoses.Reset();
	for (TActorIterator<AActor> It(GetWorld()); It; ++It)
	{
		if (!It->GetClass()->GetName().StartsWith(TEXT("BP_RefuelHose"))) continue;
		FHose H;
		H.Actor = *It;
		// Scene axes: noses +Y, aircraft right = -X. (The labels are not reliable: "SimHose_LeftPod" hangs under the
		// tanker's RIGHT wing, "SimHose_LeftWing" under the left one.)
		H.Pod = It->GetActorLocation().X < 0.0 ? EAarsPod::Right : EAarsPod::Left;
		Hoses.Add(H);
	}
}

void UAirRefuelerAarsBridge::FillWorldState(FAarsWorldState& S)
{
	S.PodLeft = FAarsPodWorld();
	S.PodRight = FAarsPodWorld();
	S.Boom = FAarsBoomWorld(); // AirRefueler has no boom
	S.Receivers.Reset();

	APawn* Pawn = UGameplayStatics::GetPlayerPawn(GetWorld(), 0);
	USceneComponent* Probe = GetComponent(Pawn, TEXT("ProbeTip"));
	const bool bMirage = Probe != nullptr;

	EAarsPhase Phase = EAarsPhase::Free;
	EAarsStation Behind = EAarsStation::None;
	double TankerZ = 0.0;

	for (const FHose& H : Hoses)
	{
		AActor* A = H.Actor.Get();
		if (!A) continue;
		int32 State = 0;
		GetInt(A, TEXT("State"), State);
		USceneComponent* Drogue = GetComponent(A, TEXT("Parachute"));
		const FVector PodLoc = A->GetActorLocation();
		TankerZ = PodLoc.Z;

		FAarsPodWorld& P = H.Pod == EAarsPod::Left ? S.PodLeft : S.PodRight;
		// States: 0 stowed, 1 trailing, 2 ready, 3 connected (probe latched), 4 rewinding, 5 cut.
		P.TipFt = (State == 0 || State == 5 || !Drogue) ? 0.0 : FVector::Dist(PodLoc, Drogue->GetComponentLocation()) / CmPerFt;
		P.bContact = State == 3 && bMirage;
		P.ReceiverId = P.bContact ? PlayerId : FString();

		if (bMirage && Drogue)
		{
			const double Range = FVector::Dist(Probe->GetComponentLocation(), Drogue->GetComponentLocation());
			EAarsPhase HosePhase = EAarsPhase::Free;
			if (State == 3) HosePhase = EAarsPhase::Contact;
			else if (State == 2 && Range < 3000.0) HosePhase = EAarsPhase::Astern;   // within 30 m of a ready drogue
			else if (State != 0) HosePhase = EAarsPhase::Approach;
			if ((int32)HosePhase > (int32)Phase)
			{
				Phase = HosePhase;
				Behind = H.Pod == EAarsPod::Left ? EAarsStation::Left : EAarsStation::Right;
			}
		}
	}

	if (bMirage)
	{
		FAarsReceiverState R;
		R.Id = PlayerId;
		R.Type = EAarsReceiverType::Other; // Mirage 2000 is not in the contract's list
		R.Behind = Behind;
		R.Phase = Phase;
		FVector Vel = FVector::ZeroVector;
		GetVector(Pawn, TEXT("Velocity"), Vel);
		// The scene's noses point +Y: the Mirage's speed relative to the tanker is Vel.Y.
		R.IasKt = FMath::Max(0.0, S.Tanker.IasKt + Vel.Y / CmPerSecPerKt);
		R.AltFt = S.Tanker.AltFt + (Pawn->GetActorLocation().Z - TankerZ) / CmPerFt;
		R.BankDeg = FMath::Clamp((double)Pawn->GetActorRotation().Roll, -90.0, 90.0);
		S.Receivers.Add(R);
	}
}

FString UAirRefuelerAarsBridge::MakeRestore() const
{
	TSharedRef<FJsonObject> O = MakeShared<FJsonObject>();
	O->SetStringField(TEXT("format"), TEXT("airrefueler/1"));
	if (APawn* Pawn = UGameplayStatics::GetPlayerPawn(GetWorld(), 0))
	{
		TSharedRef<FJsonObject> P = MakeShared<FJsonObject>();
		P->SetArrayField(TEXT("loc"), Arr(Pawn->GetActorLocation()));
		const FRotator R = Pawn->GetActorRotation();
		P->SetArrayField(TEXT("rot"), Arr(FVector(R.Pitch, R.Yaw, R.Roll)));
		FVector Vel = FVector::ZeroVector;
		if (GetVector(Pawn, TEXT("Velocity"), Vel)) P->SetArrayField(TEXT("vel"), Arr(Vel));
		O->SetObjectField(TEXT("pawn"), P);
	}
	TArray<TSharedPtr<FJsonValue>> HA;
	for (const FHose& H : Hoses)
	{
		AActor* A = H.Actor.Get();
		if (!A) continue;
		TSharedRef<FJsonObject> J = MakeShared<FJsonObject>();
		J->SetStringField(TEXT("name"), A->GetName());
		int32 State = 0;
		double Len = 0.0, Fuel = 0.0;
		GetInt(A, TEXT("State"), State);
		GetReal(A, TEXT("HoseLen"), Len);
		GetReal(A, TEXT("Fuel"), Fuel);
		J->SetNumberField(TEXT("state"), State);
		J->SetNumberField(TEXT("hose_len"), Len);
		J->SetNumberField(TEXT("fuel"), Fuel);
		HA.Add(MakeShared<FJsonValueObject>(J));
	}
	O->SetArrayField(TEXT("hoses"), HA);
	FString Out;
	TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> W = TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&Out);
	FJsonSerializer::Serialize(O, W);
	return Out;
}

bool UAirRefuelerAarsBridge::ApplyRestore(const FString& Json)
{
	TSharedPtr<FJsonObject> O;
	TSharedRef<TJsonReader<>> R = TJsonReaderFactory<>::Create(Json);
	FString Format;
	if (!FJsonSerializer::Deserialize(R, O) || !O.IsValid() || !O->TryGetStringField(TEXT("format"), Format) || Format != TEXT("airrefueler/1"))
	{
		return false;
	}
	const TSharedPtr<FJsonObject>* P;
	APawn* Pawn = UGameplayStatics::GetPlayerPawn(GetWorld(), 0);
	if (Pawn && O->TryGetObjectField(TEXT("pawn"), P))
	{
		FVector Loc, Rot, Vel;
		if (ReadArr(*P, TEXT("loc"), Loc) && ReadArr(*P, TEXT("rot"), Rot))
		{
			Pawn->SetActorLocationAndRotation(Loc, FRotator(Rot.X, Rot.Y, Rot.Z), false, nullptr, ETeleportType::TeleportPhysics);
		}
		if (ReadArr(*P, TEXT("vel"), Vel)) SetVector(Pawn, TEXT("Velocity"), Vel);
	}
	const TArray<TSharedPtr<FJsonValue>>* HA;
	if (O->TryGetArrayField(TEXT("hoses"), HA))
	{
		for (const TSharedPtr<FJsonValue>& V : *HA)
		{
			const TSharedPtr<FJsonObject> J = V->AsObject();
			FString Name;
			if (!J.IsValid() || !J->TryGetStringField(TEXT("name"), Name)) continue;
			for (const FHose& H : Hoses)
			{
				AActor* A = H.Actor.Get();
				if (!A || A->GetName() != Name) continue;
				int32 State = 0;
				double Len = 0.0, Fuel = 0.0;
				if (J->TryGetNumberField(TEXT("state"), State)) SetInt(A, TEXT("State"), State);
				if (J->TryGetNumberField(TEXT("hose_len"), Len)) SetReal(A, TEXT("HoseLen"), Len);
				if (J->TryGetNumberField(TEXT("fuel"), Fuel)) SetReal(A, TEXT("Fuel"), Fuel);
			}
		}
	}
	return true;
}

// ---- pod cameras + the one video stream ----------------------------------------------------------------------------

namespace
{
	constexpr float SensorWidthMm = 23.76f; // 16:9 digital film
	const TCHAR* PodName(EAarsPod Pod) { return Pod == EAarsPod::Left ? TEXT("Left") : TEXT("Right"); }
	float FocalMm(EAarsLens Lens) { return Lens == EAarsLens::Narrow ? UAirRefuelerAarsBridge::NarrowFocalMm : UAirRefuelerAarsBridge::WideFocalMm; }
	/** Horizontal FOV of a lens on the pod camera sensor (12 mm = 89 deg, 50 mm = 27 deg). */
	float HFovDeg(EAarsLens Lens) { return FMath::RadiansToDegrees(2.f * FMath::Atan(SensorWidthMm * 0.5f / FocalMm(Lens))); }

	void ConfigureCamera(ACineCameraActor* Cam, float Focal)
	{
		UCineCameraComponent* C = Cam->GetCineCameraComponent();
		C->Filmback.SensorWidth = SensorWidthMm;
		C->Filmback.SensorHeight = 13.365f;
		C->Filmback.RecalcSensorAspectRatio();
		C->SetConstraintAspectRatio(false);
		C->FocusSettings.FocusMethod = ECameraFocusMethod::Disable; // everything sharp, like a pod camera
		C->CurrentAperture = 22.f;
		C->SetCurrentFocalLength(Focal);
	}
}

void UAirRefuelerAarsBridge::SetupPodCameras()
{
	PodCameras.Reset();
	UWorld* W = GetWorld();
	for (const FHose& H : Hoses)
	{
		AActor* HoseActor = H.Actor.Get();
		if (!HoseActor || FindCamera(H.Pod)) continue;
		FPodCamera PC;
		PC.Pod = H.Pod;
		const FString Label = FString::Printf(TEXT("PodCam_%s"), PodName(H.Pod));
		for (TActorIterator<ACineCameraActor> It(W); It; ++It)
		{
			if (It->GetActorNameOrLabel() == Label) { PC.Camera = *It; break; }
		}
		if (!PC.Camera.IsValid())
		{
			// Default placement: 1 m aft, 0.6 m outboard and 0.4 m below the pod exit (the hose actor's origin),
			// aimed at where the drogue hangs when trailed (24 m aft, 9 deg droop). Aft = -Y, outboard = away from X = 0.
			const FVector Exit = HoseActor->GetActorLocation();
			const double Out = Exit.X < 0.0 ? -1.0 : 1.0;
			const FVector Loc = Exit + FVector(60.0 * Out, -100.0, -40.0);
			const FVector Drogue = Exit + FVector(0.0, -2400.0, -375.0);
			FActorSpawnParameters SP;
			SP.ObjectFlags |= RF_Transient;
			ACineCameraActor* Cam = W->SpawnActor<ACineCameraActor>(Loc, (Drogue - Loc).Rotation(), SP);
			if (!Cam) continue;
#if WITH_EDITOR
			Cam->SetActorLabel(Label);
#endif
			Cam->AttachToActor(HoseActor, FAttachmentTransformRules::KeepWorldTransform); // moves with the tanker
			PC.Camera = Cam;
			PC.bSpawned = true;
		}
		ConfigureCamera(PC.Camera.Get(), FocalMm(PC.Lens));
		PodCameras.Add(PC);
	}
}

UAirRefuelerAarsBridge::FPodCamera* UAirRefuelerAarsBridge::FindCamera(EAarsPod Pod)
{
	return PodCameras.FindByPredicate([Pod](const FPodCamera& C) { return C.Pod == Pod && C.Camera.IsValid(); });
}

void UAirRefuelerAarsBridge::SetupStream()
{
	UWorld* W = GetWorld();
	if (!W || PodCameras.Num() == 0) return;

	StreamTarget = NewObject<UTextureRenderTarget2D>(this, TEXT("PodCameraStream"));
	StreamTarget->RenderTargetFormat = RTF_RGBA8;
	StreamTarget->ClearColor = FLinearColor::Black;
	StreamTarget->InitAutoFormat(StreamWidth, StreamHeight);
	StreamTarget->UpdateResourceImmediate(true);

	FActorSpawnParameters SP;
	SP.ObjectFlags |= RF_Transient;
	StreamCapture = W->SpawnActor<ASceneCapture2D>(FVector::ZeroVector, FRotator::ZeroRotator, SP);
	if (!StreamCapture) return;
#if WITH_EDITOR
	StreamCapture->SetActorLabel(TEXT("PodCameraStreamCapture"));
#endif
	USceneCaptureComponent2D* C = StreamCapture->GetCaptureComponent2D();
	C->TextureTarget = StreamTarget;
	C->CaptureSource = ESceneCaptureSource::SCS_FinalColorLDR; // tonemapped, like the viewport
	C->bCaptureEveryFrame = true;
	C->bCaptureOnMovement = false;
	C->bAlwaysPersistRenderingState = true; // keeps TSR/TAA history and eye adaptation between frames
	// Measured 2026-11-26: with the same auto exposure the capture came out about 1 EV darker than the viewport.
	C->PostProcessSettings.bOverride_AutoExposureBias = true;
	C->PostProcessSettings.AutoExposureBias = 1.f;

	StreamProducer = UE::PixelStreaming2::CreateVideoProducerRenderTarget(StreamTarget);
	SelectCamera(FindCamera(SelectedPod) ? SelectedPod : PodCameras[0].Pod);
}

// Pixel Streaming creates its default streamer when PIE starts (after BeginPlay) and feeds it the PIE viewport.
// Give it the pod camera render target instead, so the stream never shows the cockpit.
void UAirRefuelerAarsBridge::FeedStreamer()
{
	if (!StreamProducer || !IPixelStreaming2Module::IsAvailable()) return;
	IPixelStreaming2Module& M = IPixelStreaming2Module::Get();
	TSharedPtr<IPixelStreaming2Streamer> S = M.FindStreamer(M.GetDefaultStreamerID());
	if (!S.IsValid()) return;
	if (S->GetVideoProducer().Pin() != StreamProducer)
	{
		S->SetVideoProducer(StreamProducer);
		if (!bLoggedStreamer)
		{
			UE_LOG(LogTemp, Display, TEXT("AirRefueler: streamer '%s' now streams the pod camera (%s)"), *S->GetId(), PodName(SelectedPod));
			bLoggedStreamer = true;
		}
	}
}

void UAirRefuelerAarsBridge::ReleaseStream()
{
	if (!StreamProducer) return;
	if (IPixelStreaming2Module::IsAvailable())
	{
		IPixelStreaming2Module& M = IPixelStreaming2Module::Get();
		TSharedPtr<IPixelStreaming2Streamer> S = M.FindStreamer(M.GetDefaultStreamerID());
		if (S.IsValid() && S->GetVideoProducer().Pin() == StreamProducer) S->SetVideoProducer(nullptr);
	}
	FlushRenderingCommands(); // the producer reads the render target on the render thread
	StreamProducer.Reset();
}

void UAirRefuelerAarsBridge::Deinitialize()
{
	ReleaseStream();
	Super::Deinitialize();
}

void UAirRefuelerAarsBridge::SelectCamera(EAarsPod Pod)
{
	FPodCamera* Cam = FindCamera(Pod);
	if (!Cam || !StreamCapture) return;
	SelectedPod = Pod;
	StreamCapture->AttachToActor(Cam->Camera.Get(), FAttachmentTransformRules::SnapToTargetNotIncludingScale);
	StreamCapture->GetCaptureComponent2D()->FOVAngle = HFovDeg(Cam->Lens);
}

void UAirRefuelerAarsBridge::HandleCameraSelect(const FAarsCameraSelect& M)
{
	SelectCamera(M.Pod);
}

void UAirRefuelerAarsBridge::HandleCameraLens(const FAarsCameraLens& M)
{
	SetLens(M.Pod, M.Lens);
}

void UAirRefuelerAarsBridge::SetLens(EAarsPod Pod, EAarsLens Lens)
{
	FPodCamera* C = FindCamera(Pod);
	if (!C) return;
	C->Lens = Lens;
	C->Camera->GetCineCameraComponent()->SetCurrentFocalLength(FocalMm(Lens));
	if (Pod == SelectedPod && StreamCapture) StreamCapture->GetCaptureComponent2D()->FOVAngle = HFovDeg(Lens);
}

void UAirRefuelerAarsBridge::PollKeys()
{
	APlayerController* PC = GetWorld() ? GetWorld()->GetFirstPlayerController() : nullptr;
	if (!PC) return;
	if (PC->WasInputKeyJustPressed(EKeys::One)) SelectCamera(EAarsPod::Left);
	if (PC->WasInputKeyJustPressed(EKeys::Two)) SelectCamera(EAarsPod::Right);
	if (PC->WasInputKeyJustPressed(EKeys::N))
	{
		if (FPodCamera* C = FindCamera(SelectedPod)) SetLens(SelectedPod, C->Lens == EAarsLens::Wide ? EAarsLens::Narrow : EAarsLens::Wide);
	}
}

UAirRefuelerAarsBridge* UAirRefuelerAarsBridge::FindRunning()
{
	if (!GEngine) return nullptr;
	for (const FWorldContext& Ctx : GEngine->GetWorldContexts())
	{
		UWorld* W = Ctx.World();
		if (W && (Ctx.WorldType == EWorldType::PIE || Ctx.WorldType == EWorldType::Game) && W->HasBegunPlay())
		{
			if (UAirRefuelerAarsBridge* B = W->GetSubsystem<UAirRefuelerAarsBridge>()) return B;
		}
	}
	return nullptr;
}

namespace
{
	bool ParsePod(const FString& S, EAarsPod& Out)
	{
		if (S.StartsWith(TEXT("L"), ESearchCase::IgnoreCase)) { Out = EAarsPod::Left; return true; }
		if (S.StartsWith(TEXT("R"), ESearchCase::IgnoreCase)) { Out = EAarsPod::Right; return true; }
		return false;
	}

	FAutoConsoleCommand GAarsCameraCmd(
		TEXT("aars.Camera"),
		TEXT("Pod camera on the video stream, like camera.select: aars.Camera Left|Right"),
		FConsoleCommandWithArgsDelegate::CreateLambda([](const TArray<FString>& Args)
		{
			UAirRefuelerAarsBridge* B = UAirRefuelerAarsBridge::FindRunning();
			EAarsPod Pod;
			if (B && Args.Num() >= 1 && ParsePod(Args[0], Pod)) B->SelectCamera(Pod);
		}));

	FAutoConsoleCommand GAarsLensCmd(
		TEXT("aars.Lens"),
		TEXT("Pod camera lens, like camera.lens: aars.Lens Left|Right Wide|Narrow"),
		FConsoleCommandWithArgsDelegate::CreateLambda([](const TArray<FString>& Args)
		{
			UAirRefuelerAarsBridge* B = UAirRefuelerAarsBridge::FindRunning();
			EAarsPod Pod;
			if (!B || Args.Num() < 2 || !ParsePod(Args[0], Pod)) return;
			B->SetLens(Pod, Args[1].StartsWith(TEXT("N"), ESearchCase::IgnoreCase) ? EAarsLens::Narrow : EAarsLens::Wide);
		}));
}
