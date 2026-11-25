#include "AarsFakeWorldCommandlet.h"

#include "AarsCodec.h"
#include "AarsLinkServer.h"
#include "Dom/JsonObject.h"
#include "HAL/PlatformProcess.h"
#include "HAL/PlatformTime.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

DEFINE_LOG_CATEGORY_STATIC(LogAarsFakeWorld, Log, All);

namespace
{
	struct FPodSystem
	{
		double PayoutFt = 0.0;
		bool bAttached = false;
		bool bCut = false;
		double FuelPressurePsi = 0.0;
		double FlowLbMin = 0.0;
		EAarsLens Lens = EAarsLens::Wide;
	};

	/** The stand-in World. Units are the contract's. */
	struct FFakeWorld
	{
		double TimeMs = 0.0;
		double ClockScale = 1.0;
		bool bPaused = false;
		bool bReplaying = false;
		FAarsTanker Tanker;
		FPodSystem Pods[2];
		FAarsBoomDrive BoomDrive;
		TArray<FAarsReceiverState> Receivers;
		int64 RestoreFailures = 0;
		int64 Replays = 0;

		FFakeWorld()
		{
			Tanker.IasKt = 250.0;
			Tanker.AltFt = 25000.0;
			Tanker.PitchDeg = 2.1;
			Tanker.HeadingDeg = 90.0;
			Tanker.Ap = EAarsAutopilot::Cmd;
		}

		FAarsReceiverState* FindReceiver(const FString& Id)
		{
			return Receivers.FindByPredicate([&](const FAarsReceiverState& R) { return R.Id == Id; });
		}

		const FAarsReceiverState* ReceiverBehind(EAarsStation Station) const
		{
			return Receivers.FindByPredicate([&](const FAarsReceiverState& R) { return R.Behind == Station; });
		}

		void Step(double DtSeconds)
		{
			if (bPaused || bReplaying) return;
			const double Dt = DtSeconds * ClockScale;
			TimeMs += Dt * 1000.0;
			// Rate-one turn from bank: deg/s = 1091 * tan(bank) / TAS[kt] (IAS used as TAS here).
			if (Tanker.IasKt > 1.0 && FMath::Abs(Tanker.BankDeg) > 0.01)
			{
				Tanker.HeadingDeg += 1091.0 * FMath::Tan(FMath::DegreesToRadians(Tanker.BankDeg)) / Tanker.IasKt * Dt;
				Tanker.HeadingDeg = FMath::Fmod(Tanker.HeadingDeg + 360.0, 360.0);
			}
			for (FAarsReceiverState& R : Receivers)
			{
				R.IasKt = Tanker.IasKt;
				R.AltFt = Tanker.AltFt - (R.Phase == EAarsPhase::Free ? 1000.0 : 0.0);
				R.BankDeg = Tanker.BankDeg;
			}
		}

		FAarsPodWorld PodWorld(EAarsPod Pod) const
		{
			const FPodSystem& P = Pods[(int32)Pod];
			FAarsPodWorld W;
			const FAarsReceiverState* R = ReceiverBehind(Pod == EAarsPod::Left ? EAarsStation::Left : EAarsStation::Right);
			W.bContact = !P.bCut && R && R->Phase == EAarsPhase::Contact && P.PayoutFt > 0.0;
			W.ReceiverId = R ? R->Id : FString();
			// In contact the receiver has pushed the drogue in by ~6 ft (contract scenario, step 4).
			W.TipFt = P.bCut ? 0.0 : (W.bContact ? FMath::Max(0.0, P.PayoutFt - 6.0) : P.PayoutFt);
			return W;
		}

		FAarsBoomWorld BoomWorld() const
		{
			FAarsBoomWorld B;
			B.Tip.ElDeg = BoomDrive.ElDeg;
			B.Tip.AzDeg = BoomDrive.AzDeg;
			B.Tip.TeleFt = BoomDrive.TeleFt;
			const FAarsReceiverState* R = ReceiverBehind(EAarsStation::Boom);
			if (R)
			{
				B.ReceiverId = R->Id;
				if (R->Phase == EAarsPhase::Astern || R->Phase == EAarsPhase::Contact)
				{
					const double T = TimeMs / 1000.0;
					B.bHoleValid = true;
					B.Hole.AzDeg = 2.5 + 0.3 * FMath::Sin(T * 0.7);
					B.Hole.ElDeg = 30.6 + 0.2 * FMath::Sin(T * 0.5);
					B.Hole.RangeFt = R->Phase == EAarsPhase::Contact ? 12.4 : 25.0;
					B.Hole.DAzDps = 0.3 * 0.7 * FMath::Cos(T * 0.7);
					B.Hole.DElDps = 0.2 * 0.5 * FMath::Cos(T * 0.5);
					B.Hole.DRangeFps = 0.0;
					B.bTrackBoxValid = true;
					B.TrackX = 0.42; B.TrackY = 0.38; B.TrackW = 0.20; B.TrackH = 0.14;
					B.bContact = R->Phase == EAarsPhase::Contact;
					if (B.bContact && BoomDrive.bAttached)
					{
						// Coupled: the boom tip moves with the receiver.
						B.Tip.AzDeg = B.Hole.AzDeg;
						B.Tip.ElDeg = B.Hole.ElDeg;
						B.Tip.TeleFt = B.Hole.RangeFt;
					}
				}
			}
			return B;
		}

		FAarsWorldState State() const
		{
			FAarsWorldState S;
			S.TMs = (int64)TimeMs;
			S.ClockScale = ClockScale;
			S.bPaused = bPaused;
			S.Tanker = Tanker;
			S.PodLeft = PodWorld(EAarsPod::Left);
			S.PodRight = PodWorld(EAarsPod::Right);
			S.Boom = BoomWorld();
			S.Receivers = Receivers;
			return S;
		}

		// ---- restore: the World's own format (opaque to the Simulator) ----
		FString Restore() const
		{
			TSharedRef<FJsonObject> O = MakeShared<FJsonObject>();
			O->SetStringField(TEXT("format"), TEXT("aars-fake-world/1"));
			O->SetNumberField(TEXT("time_ms"), TimeMs);
			O->SetNumberField(TEXT("clock_scale"), ClockScale);
			O->SetBoolField(TEXT("paused"), bPaused);
			TSharedRef<FJsonObject> T = MakeShared<FJsonObject>();
			T->SetNumberField(TEXT("ias_kt"), Tanker.IasKt);
			T->SetNumberField(TEXT("alt_ft"), Tanker.AltFt);
			T->SetNumberField(TEXT("bank_deg"), Tanker.BankDeg);
			T->SetNumberField(TEXT("pitch_deg"), Tanker.PitchDeg);
			T->SetNumberField(TEXT("heading_deg"), Tanker.HeadingDeg);
			T->SetStringField(TEXT("ap"), AarsCodec::ToString(Tanker.Ap));
			O->SetObjectField(TEXT("tanker"), T);
			TArray<TSharedPtr<FJsonValue>> Pa;
			for (const FPodSystem& P : Pods)
			{
				TSharedRef<FJsonObject> J = MakeShared<FJsonObject>();
				J->SetNumberField(TEXT("payout_ft"), P.PayoutFt);
				J->SetBoolField(TEXT("attached"), P.bAttached);
				J->SetBoolField(TEXT("cut"), P.bCut);
				Pa.Add(MakeShared<FJsonValueObject>(J));
			}
			O->SetArrayField(TEXT("pods"), Pa);
			TSharedRef<FJsonObject> Bo = MakeShared<FJsonObject>();
			Bo->SetNumberField(TEXT("el_deg"), BoomDrive.ElDeg);
			Bo->SetNumberField(TEXT("az_deg"), BoomDrive.AzDeg);
			Bo->SetNumberField(TEXT("tele_ft"), BoomDrive.TeleFt);
			Bo->SetBoolField(TEXT("attached"), BoomDrive.bAttached);
			O->SetObjectField(TEXT("boom"), Bo);
			TArray<TSharedPtr<FJsonValue>> Ra;
			for (const FAarsReceiverState& R : Receivers)
			{
				TSharedRef<FJsonObject> J = MakeShared<FJsonObject>();
				J->SetStringField(TEXT("id"), R.Id);
				J->SetNumberField(TEXT("type"), (int32)R.Type);
				J->SetNumberField(TEXT("behind"), (int32)R.Behind);
				J->SetNumberField(TEXT("phase"), (int32)R.Phase);
				Ra.Add(MakeShared<FJsonValueObject>(J));
			}
			O->SetArrayField(TEXT("receivers"), Ra);
			FString Out;
			TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> W = TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&Out);
			FJsonSerializer::Serialize(O, W);
			return Out;
		}

		bool ApplyRestore(const FString& Json)
		{
			TSharedPtr<FJsonObject> O;
			TSharedRef<TJsonReader<>> R = TJsonReaderFactory<>::Create(Json);
			FString Format;
			if (!FJsonSerializer::Deserialize(R, O) || !O.IsValid() || !O->TryGetStringField(TEXT("format"), Format) || Format != TEXT("aars-fake-world/1"))
			{
				++RestoreFailures;
				return false;
			}
			O->TryGetNumberField(TEXT("time_ms"), TimeMs);
			O->TryGetNumberField(TEXT("clock_scale"), ClockScale);
			O->TryGetBoolField(TEXT("paused"), bPaused);
			const TSharedPtr<FJsonObject>* T;
			if (O->TryGetObjectField(TEXT("tanker"), T))
			{
				(*T)->TryGetNumberField(TEXT("ias_kt"), Tanker.IasKt);
				(*T)->TryGetNumberField(TEXT("alt_ft"), Tanker.AltFt);
				(*T)->TryGetNumberField(TEXT("bank_deg"), Tanker.BankDeg);
				(*T)->TryGetNumberField(TEXT("pitch_deg"), Tanker.PitchDeg);
				(*T)->TryGetNumberField(TEXT("heading_deg"), Tanker.HeadingDeg);
				FString Ap;
				if ((*T)->TryGetStringField(TEXT("ap"), Ap)) Tanker.Ap = Ap == TEXT("OFF") ? EAarsAutopilot::Off : EAarsAutopilot::Cmd;
			}
			const TArray<TSharedPtr<FJsonValue>>* Pa;
			if (O->TryGetArrayField(TEXT("pods"), Pa))
			{
				for (int32 I = 0; I < FMath::Min(2, Pa->Num()); ++I)
				{
					const TSharedPtr<FJsonObject> J = (*Pa)[I]->AsObject();
					J->TryGetNumberField(TEXT("payout_ft"), Pods[I].PayoutFt);
					J->TryGetBoolField(TEXT("attached"), Pods[I].bAttached);
					J->TryGetBoolField(TEXT("cut"), Pods[I].bCut);
				}
			}
			const TSharedPtr<FJsonObject>* Bo;
			if (O->TryGetObjectField(TEXT("boom"), Bo))
			{
				(*Bo)->TryGetNumberField(TEXT("el_deg"), BoomDrive.ElDeg);
				(*Bo)->TryGetNumberField(TEXT("az_deg"), BoomDrive.AzDeg);
				(*Bo)->TryGetNumberField(TEXT("tele_ft"), BoomDrive.TeleFt);
				(*Bo)->TryGetBoolField(TEXT("attached"), BoomDrive.bAttached);
			}
			const TArray<TSharedPtr<FJsonValue>>* Ra;
			if (O->TryGetArrayField(TEXT("receivers"), Ra))
			{
				Receivers.Reset();
				for (const TSharedPtr<FJsonValue>& V : *Ra)
				{
					const TSharedPtr<FJsonObject> J = V->AsObject();
					FAarsReceiverState Rs;
					int32 Type = 0, Behind = 0, Phase = 0;
					J->TryGetStringField(TEXT("id"), Rs.Id);
					J->TryGetNumberField(TEXT("type"), Type);
					J->TryGetNumberField(TEXT("behind"), Behind);
					J->TryGetNumberField(TEXT("phase"), Phase);
					Rs.Type = (EAarsReceiverType)FMath::Clamp(Type, 0, 5);
					Rs.Behind = (EAarsStation)FMath::Clamp(Behind, 0, 3);
					Rs.Phase = (EAarsPhase)FMath::Clamp(Phase, 0, 4);
					Receivers.Add(Rs);
				}
			}
			Step(0.0);
			return true;
		}
	};

	EAarsPhase PhaseFor(EAarsReceiverAction A)
	{
		switch (A)
		{
		case EAarsReceiverAction::Approach: return EAarsPhase::Approach;
		case EAarsReceiverAction::Astern: return EAarsPhase::Astern;
		case EAarsReceiverAction::Contact: return EAarsPhase::Contact;
		case EAarsReceiverAction::Disconnect: return EAarsPhase::Astern;
		case EAarsReceiverAction::Breakaway: return EAarsPhase::Departing;
		case EAarsReceiverAction::Leave: return EAarsPhase::Departing;
		}
		return EAarsPhase::Free;
	}
}

UAarsFakeWorldCommandlet::UAarsFakeWorldCommandlet()
{
	LogToConsole = true;
}

int32 UAarsFakeWorldCommandlet::Main(const FString& Params)
{
	int32 Port = 8765, Hz = 60;
	double Seconds = 0.0;
	FString Bind, OutPath, ReadyPath;
	FParse::Value(*Params, TEXT("port="), Port);
	FParse::Value(*Params, TEXT("hz="), Hz);
	FParse::Value(*Params, TEXT("seconds="), Seconds);
	FParse::Value(*Params, TEXT("bind="), Bind);
	FParse::Value(*Params, TEXT("out="), OutPath);
	FParse::Value(*Params, TEXT("ready="), ReadyPath);
	const bool bRestoreStream = FParse::Param(*Params, TEXT("restore"));
	const bool bAllowQuit = FParse::Param(*Params, TEXT("allowquit"));
	const bool bBadValues = FParse::Param(*Params, TEXT("badvalues")); // test: feed out-of-contract values to the codec

	FFakeWorld W;
	FAarsLinkServer Link;
	bool bQuit = false;

	Link.OnPodHose.AddLambda([&](const FAarsPodHose& M)
	{
		FPodSystem& P = W.Pods[(int32)M.Pod];
		if (P.bCut) return; // gone for good
		P.PayoutFt = M.PayoutFt;
		P.bAttached = M.bAttached;
		P.bCut = M.bCut;
	});
	Link.OnPodFluid.AddLambda([&](const FAarsPodFluid& M)
	{
		W.Pods[(int32)M.Pod].FuelPressurePsi = M.FuelPressurePsi;
		W.Pods[(int32)M.Pod].FlowLbMin = M.FlowLbMin;
	});
	Link.OnCameraLens.AddLambda([&](const FAarsCameraLens& M) { W.Pods[(int32)M.Pod].Lens = M.Lens; });
	Link.OnBoomDrive.AddLambda([&](const FAarsBoomDrive& M) { W.BoomDrive = M; });
	Link.OnClockSet.AddLambda([&](const FAarsClockSet& M) { W.ClockScale = M.Scale; W.bPaused = M.bPaused; });
	Link.OnTankerSet.AddLambda([&](const FAarsTankerSet& M)
	{
		if (M.bHasIasKt) W.Tanker.IasKt = M.IasKt;
		if (M.bHasAltFt) W.Tanker.AltFt = M.AltFt;
		if (M.bHasBankDeg) W.Tanker.BankDeg = M.BankDeg;
		if (M.bHasAp) W.Tanker.Ap = M.Ap;
	});
	Link.OnReceiverAdd.AddLambda([&](const FAarsReceiverAdd& M)
	{
		FAarsReceiverState* R = W.FindReceiver(M.Id);
		if (!R) R = &W.Receivers.AddDefaulted_GetRef();
		R->Id = M.Id;
		R->Type = M.ReceiverType;
		R->Behind = M.Behind;
		R->Phase = EAarsPhase::Free;
		W.Step(0.0);
	});
	Link.OnReceiverCommand.AddLambda([&](const FAarsReceiverCommand& M)
	{
		if (FAarsReceiverState* R = W.FindReceiver(M.Id)) R->Phase = PhaseFor(M.Action);
		else UE_LOG(LogAarsFakeWorld, Warning, TEXT("receiver.command for unknown receiver %s"), *M.Id);
	});
	Link.OnReceiverRemove.AddLambda([&](const FAarsReceiverRemove& M) { W.Receivers.RemoveAll([&](const FAarsReceiverState& R) { return R.Id == M.Id; }); });
	Link.OnSnapshotRequest.AddLambda([&](const FAarsSnapshotRequest& M) { Link.SendSnapshotReply(M.RequestId, (int64)W.TimeMs, W.Restore()); });
	Link.OnWorldSet.AddLambda([&](const FAarsWorldSet& M)
	{
		W.bReplaying = true;
		++W.Replays;
		if (!W.ApplyRestore(M.RestoreJson)) UE_LOG(LogAarsFakeWorld, Error, TEXT("world.set: restore not understood (no contract message for this yet, open question 9)"));
		W.TimeMs = (double)M.TMs;
	});
	Link.OnWorldResume.AddLambda([&]() { W.bReplaying = false; });
	Link.OnRejected.AddLambda([&](const FString& Raw, const FString&)
	{
		if (bAllowQuit && Raw.Contains(TEXT("\"quit\""))) bQuit = true;
	});

	if (!Link.Start(Port, Bind, TEXT("unreal-fake-world"))) return 1;
	if (!ReadyPath.IsEmpty()) FFileHelper::SaveStringToFile(TEXT("ready"), *ReadyPath);
	UE_LOG(LogAarsFakeWorld, Display, TEXT("fake World running at %d Hz%s"), Hz, bRestoreStream ? TEXT(", restore in world.state at 30 Hz") : TEXT(""));

	const double Period = 1.0 / FMath::Max(1, Hz);
	double Next = FPlatformTime::Seconds(), Last = Next;
	const double End = Seconds > 0.0 ? Next + Seconds : TNumericLimits<double>::Max();
	int64 Frame = 0;

	while (!bQuit && !IsEngineExitRequested() && FPlatformTime::Seconds() < End)
	{
		const double Now = FPlatformTime::Seconds();
		Link.Receive();
		W.Step(Now - Last);
		Last = Now;

		FAarsWorldState S = W.State();
		if (bRestoreStream && (Frame % 2) == 0) S.RestoreJson = W.Restore();
		if (bBadValues)
		{
			S.Tanker.HeadingDeg = 370.0 + Frame;
			S.Tanker.BankDeg = 95.0;
			S.Tanker.PitchDeg = -120.0;
			S.Tanker.IasKt = -5.0;
			S.Tanker.AltFt = FMath::Sqrt(-1.0); // NaN
			S.ClockScale = 0.0;
			S.PodLeft.TipFt = -1.0;
			S.PodRight.ReceiverId = FString::ChrN(40, TEXT('R'));
			S.Boom.bTrackBoxValid = true;
			S.Boom.TrackX = 1.2; S.Boom.TrackY = -0.1; S.Boom.TrackW = 0.5; S.Boom.TrackH = 0.5;
			S.Receivers.Add(FAarsReceiverState()); // empty id: must be skipped
			S.RestoreJson = TEXT("[1,2]");          // not an object: must be omitted
		}
		Link.SendWorldState(S);
		Link.Flush();
		++Frame;

		Next += Period;
		for (;;)
		{
			const double Rem = Next - FPlatformTime::Seconds();
			if (Rem <= 0) break;
			FPlatformProcess::SleepNoStats(Rem > 0.002 ? (float)(Rem - 0.0015) : 0.0f);
		}
	}

	const FAarsLinkServer::FStats& St = Link.GetStats();
	TSharedRef<FJsonObject> R = MakeShared<FJsonObject>();
	R->SetNumberField(TEXT("frames"), Frame);
	R->SetNumberField(TEXT("connects"), St.Connects);
	R->SetNumberField(TEXT("disconnects"), St.Disconnects);
	R->SetNumberField(TEXT("replaced"), St.Replaced);
	R->SetNumberField(TEXT("received"), St.Received);
	R->SetNumberField(TEXT("accepted"), St.Accepted);
	R->SetNumberField(TEXT("rejected"), St.Rejected);
	R->SetNumberField(TEXT("stale"), St.Stale);
	R->SetNumberField(TEXT("ignored_inactive"), St.IgnoredInactive);
	R->SetNumberField(TEXT("ignored_version"), St.IgnoredVersion);
	R->SetNumberField(TEXT("sent"), St.Sent);
	R->SetNumberField(TEXT("fixes"), St.Fixes);
	R->SetNumberField(TEXT("replays"), W.Replays);
	R->SetNumberField(TEXT("restore_failures"), W.RestoreFailures);
	R->SetStringField(TEXT("peer_name"), St.PeerName);
	R->SetStringField(TEXT("peer_version"), St.PeerVersion);
	R->SetBoolField(TEXT("version_mismatch"), St.bVersionMismatch);
	TSharedRef<FJsonObject> ByType = MakeShared<FJsonObject>();
	for (const TPair<EAarsInboundType, int64>& P : St.ByType) ByType->SetNumberField(AarsCodec::ToString(P.Key), P.Value);
	R->SetObjectField(TEXT("accepted_by_type"), ByType);
	TArray<TSharedPtr<FJsonValue>> Rej;
	for (const FString& S : St.LastRejects) Rej.Add(MakeShared<FJsonValueString>(S));
	R->SetArrayField(TEXT("last_rejects"), Rej);
	TArray<TSharedPtr<FJsonValue>> Fix;
	for (const FString& S : St.LastFixes) Fix.Add(MakeShared<FJsonValueString>(S));
	R->SetArrayField(TEXT("last_fixes"), Fix);

	FString Out;
	TSharedRef<TJsonWriter<>> Wr = TJsonWriterFactory<>::Create(&Out);
	FJsonSerializer::Serialize(R, Wr);
	if (!OutPath.IsEmpty()) FFileHelper::SaveStringToFile(Out, *OutPath, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
	UE_LOG(LogAarsFakeWorld, Display, TEXT("%s"), *Out);
	return 0;
}
