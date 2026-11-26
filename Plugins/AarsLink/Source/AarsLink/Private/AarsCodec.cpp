#include "AarsCodec.h"

#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Policies/CondensedJsonPrintPolicy.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

const TCHAR* const AarsCodec::ContractVersion = TEXT("0.2");

namespace
{
	// Enum <-> contract strings. Order matches the UENUMs.
	const TCHAR* const PodNames[] = { TEXT("LEFT"), TEXT("RIGHT") };
	const TCHAR* const StationNames[] = { TEXT("null"), TEXT("LEFT"), TEXT("RIGHT"), TEXT("BOOM") };
	const TCHAR* const ReceiverTypeNames[] = { TEXT("RAFALE"), TEXT("F/A-18"), TEXT("C-130"), TEXT("F-35"), TEXT("F-16"), TEXT("OTHER") };
	const TCHAR* const PhaseNames[] = { TEXT("FREE"), TEXT("APPROACH"), TEXT("ASTERN"), TEXT("CONTACT"), TEXT("DEPARTING") };
	const TCHAR* const ApNames[] = { TEXT("CMD"), TEXT("OFF") };
	const TCHAR* const LensNames[] = { TEXT("WIDE"), TEXT("NARROW") };
	const TCHAR* const ActionNames[] = { TEXT("APPROACH"), TEXT("ASTERN"), TEXT("CONTACT"), TEXT("DISCONNECT"), TEXT("BREAKAWAY"), TEXT("LEAVE") };
	const TCHAR* const InboundNames[] = { TEXT("none"), TEXT("hello"), TEXT("ping"), TEXT("pod.hose"), TEXT("pod.fluid"), TEXT("boom.drive"), TEXT("boom.fluid"),
		TEXT("camera.lens"), TEXT("clock.set"), TEXT("snapshot.request"), TEXT("world.set"), TEXT("world.resume"), TEXT("tanker.set"),
		TEXT("receiver.add"), TEXT("receiver.command"), TEXT("receiver.remove"), TEXT("camera.select") };

	template <typename E, int32 N>
	const TCHAR* EnumName(E V, const TCHAR* const (&Names)[N])
	{
		const int32 I = (int32)V;
		return (I >= 0 && I < N) ? Names[I] : TEXT("?");
	}

	// ------------------------------------------------------------------------------------------------------------
	// Writer: hand-made so numbers come out short ("2.1", not "2.1000000000000001") and integers stay integers.

	struct FJsonOut
	{
		FString S;
		TArray<bool> HasItem; // per open object/array: something was written already (needs a comma)

		void Prefix(const TCHAR* K)
		{
			if (HasItem.Num() > 0)
			{
				if (HasItem.Last()) S += TEXT(',');
				HasItem.Last() = true;
			}
			if (K)
			{
				S += TEXT('"');
				S += K; // keys are fixed contract names, no escaping needed
				S += TEXT("\":");
			}
		}
		void BeginObject(const TCHAR* K = nullptr) { Prefix(K); S += TEXT('{'); HasItem.Add(false); }
		void EndObject() { HasItem.Pop(); S += TEXT('}'); }
		void BeginArray(const TCHAR* K = nullptr) { Prefix(K); S += TEXT('['); HasItem.Add(false); }
		void EndArray() { HasItem.Pop(); S += TEXT(']'); }
		void Emit(const TCHAR* K, const FString& Raw) { Prefix(K); S += Raw; }

		static FString Number(double V)
		{
			if (!FMath::IsFinite(V)) V = 0.0;
			if (V == FMath::RoundToDouble(V) && FMath::Abs(V) < 1e15) return FString::Printf(TEXT("%lld"), (long long)V);
			return FString::Printf(TEXT("%.10g"), V);
		}
		static FString Quote(const FString& In)
		{
			FString R(TEXT("\""));
			for (TCHAR C : In)
			{
				switch (C)
				{
				case TEXT('"'): R += TEXT("\\\""); break;
				case TEXT('\\'): R += TEXT("\\\\"); break;
				case TEXT('\n'): R += TEXT("\\n"); break;
				case TEXT('\r'): R += TEXT("\\r"); break;
				case TEXT('\t'): R += TEXT("\\t"); break;
				default:
					if (C < 0x20) R += FString::Printf(TEXT("\\u%04x"), (int32)C);
					else R += C;
				}
			}
			R += TEXT('"');
			return R;
		}

		void Num(const TCHAR* K, double V) { Emit(K, Number(V)); }
		void Int(const TCHAR* K, int64 V) { Emit(K, FString::Printf(TEXT("%lld"), (long long)V)); }
		void Str(const TCHAR* K, const FString& V) { Emit(K, Quote(V)); }
		void Bool(const TCHAR* K, bool V) { Emit(K, V ? TEXT("true") : TEXT("false")); }
		void Null(const TCHAR* K) { Emit(K, TEXT("null")); }
		void IdOrNull(const TCHAR* K, const FString& V) { V.IsEmpty() ? Null(K) : Str(K, V); }
	};

	// Value fixing for world.state, so the World never sends something the schema rejects.
	struct FFixer
	{
		TArray<FString>* Fixes;
		double Num(const TCHAR* What, double V)
		{
			if (FMath::IsFinite(V)) return V;
			if (Fixes) Fixes->Add(FString::Printf(TEXT("%s not finite -> 0"), What));
			return 0.0;
		}
		double Clamp(const TCHAR* What, double V, double Lo, double Hi)
		{
			V = Num(What, V);
			const double C = FMath::Clamp(V, Lo, Hi);
			if (C != V && Fixes) Fixes->Add(FString::Printf(TEXT("%s %g clamped to %g"), What, V, C));
			return C;
		}
		double NonNeg(const TCHAR* What, double V) { return Clamp(What, V, 0.0, TNumericLimits<double>::Max()); }
		double Heading(double V)
		{
			V = Num(TEXT("tanker.heading_deg"), V);
			double H = FMath::Fmod(V, 360.0);
			if (H < 0.0) H += 360.0;
			if (H >= 360.0) H = 0.0;
			if (H != V && Fixes) Fixes->Add(FString::Printf(TEXT("tanker.heading_deg %g wrapped to %g"), V, H));
			return H;
		}
		FString Id(const TCHAR* What, const FString& V)
		{
			if (V.Len() <= 32) return V;
			if (Fixes) Fixes->Add(FString::Printf(TEXT("%s longer than 32 chars, cut"), What));
			return V.Left(32);
		}
	};

	void WritePod(FJsonOut& J, const TCHAR* K, const FAarsPodWorld& P, FFixer& F)
	{
		J.BeginObject(K);
		J.Num(TEXT("tip_ft"), F.NonNeg(TEXT("pods.tip_ft"), P.TipFt));
		J.Bool(TEXT("contact"), P.bContact);
		J.IdOrNull(TEXT("receiver_id"), F.Id(TEXT("pods.receiver_id"), P.ReceiverId));
		J.EndObject();
	}

	// ------------------------------------------------------------------------------------------------------------
	// Strict reader

	class FReader
	{
	public:
		FReader(const TSharedPtr<FJsonObject>& InObj, const FString& InPath, FString& InError)
			: Obj(InObj), Path(InPath), Error(InError) {}

		bool Fail(const FString& Key, const FString& Msg)
		{
			if (Error.IsEmpty()) Error = FString::Printf(TEXT("%s%s%s: %s"), *Path, Key.IsEmpty() ? TEXT("") : TEXT("."), *Key, *Msg);
			return false;
		}

		bool Has(const TCHAR* K) const { return Obj->Values.Contains(K); }

		TSharedPtr<FJsonValue> Get(const TCHAR* K, bool bRequired)
		{
			Seen.Add(K);
			const TSharedPtr<FJsonValue>* V = Obj->Values.Find(K);
			if (!V || !V->IsValid())
			{
				if (bRequired) Fail(K, TEXT("missing"));
				return nullptr;
			}
			return *V;
		}

		bool Number(const TCHAR* K, double& Out, double Min = -TNumericLimits<double>::Max(), double Max = TNumericLimits<double>::Max(),
			bool bExclusiveMin = false, bool bExclusiveMax = false, bool bRequired = true)
		{
			TSharedPtr<FJsonValue> V = Get(K, bRequired);
			if (!V) return !bRequired;
			if (V->Type != EJson::Number) return Fail(K, TEXT("must be a number"));
			const double D = V->AsNumber();
			if (!FMath::IsFinite(D)) return Fail(K, TEXT("not finite"));
			if (bExclusiveMin ? D <= Min : D < Min) return Fail(K, FString::Printf(TEXT("%g below %s%g"), D, bExclusiveMin ? TEXT(">") : TEXT(">="), Min));
			if (bExclusiveMax ? D >= Max : D > Max) return Fail(K, FString::Printf(TEXT("%g above %s%g"), D, bExclusiveMax ? TEXT("<") : TEXT("<="), Max));
			Out = D;
			return true;
		}

		bool Integer(const TCHAR* K, int64& Out)
		{
			TSharedPtr<FJsonValue> V = Get(K, true);
			if (!V) return false;
			if (V->Type != EJson::Number) return Fail(K, TEXT("must be an integer"));
			const double D = V->AsNumber();
			if (!FMath::IsFinite(D) || D != FMath::FloorToDouble(D)) return Fail(K, TEXT("must be an integer"));
			if (D < 0.0) return Fail(K, TEXT("must be >= 0"));
			if (D > 9007199254740991.0) return Fail(K, TEXT("too large"));
			Out = (int64)D;
			return true;
		}

		bool Bool(const TCHAR* K, bool& Out)
		{
			TSharedPtr<FJsonValue> V = Get(K, true);
			if (!V) return false;
			if (V->Type != EJson::Boolean) return Fail(K, TEXT("must be true or false"));
			Out = V->AsBool();
			return true;
		}

		bool String(const TCHAR* K, FString& Out, int32 MinLen = 0, int32 MaxLen = MAX_int32)
		{
			TSharedPtr<FJsonValue> V = Get(K, true);
			if (!V) return false;
			if (V->Type != EJson::String) return Fail(K, TEXT("must be a string"));
			Out = V->AsString();
			if (Out.Len() < MinLen) return Fail(K, FString::Printf(TEXT("shorter than %d"), MinLen));
			if (Out.Len() > MaxLen) return Fail(K, FString::Printf(TEXT("longer than %d"), MaxLen));
			return true;
		}

		bool Id(const TCHAR* K, FString& Out) { return String(K, Out, 1, 32); }

		template <typename E, int32 N>
		bool Enum(const TCHAR* K, E& Out, const TCHAR* const (&Names)[N], int32 First = 0, bool bRequired = true)
		{
			TSharedPtr<FJsonValue> V = Get(K, bRequired);
			if (!V) return !bRequired;
			if (V->Type != EJson::String) return Fail(K, TEXT("must be a string"));
			const FString S = V->AsString();
			for (int32 I = First; I < N; ++I)
			{
				if (S.Equals(Names[I], ESearchCase::CaseSensitive))
				{
					Out = (E)I;
					return true;
				}
			}
			FString Allowed;
			for (int32 I = First; I < N; ++I) Allowed += (I > First ? TEXT(", ") : TEXT("")) + FString(Names[I]);
			return Fail(K, FString::Printf(TEXT("'%s' is not one of %s"), *S, *Allowed));
		}

		bool Object(const TCHAR* K, TSharedPtr<FJsonObject>& Out)
		{
			TSharedPtr<FJsonValue> V = Get(K, true);
			if (!V) return false;
			if (V->Type != EJson::Object) return Fail(K, TEXT("must be an object"));
			Out = V->AsObject();
			return true;
		}

		/** No field other than the ones read so far (additionalProperties: false). */
		bool NoOtherFields()
		{
			for (const TPair<FString, TSharedPtr<FJsonValue>>& P : Obj->Values)
			{
				if (!Seen.Contains(P.Key)) return Fail(P.Key, TEXT("unknown field"));
			}
			return true;
		}

		int32 NumFields() const { return Obj->Values.Num(); }

	private:
		TSharedPtr<FJsonObject> Obj;
		FString Path;
		FString& Error;
		TSet<FString> Seen;
	};

	FString ToCondensed(const TSharedPtr<FJsonObject>& Obj)
	{
		FString Out;
		TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> W = TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&Out);
		FJsonSerializer::Serialize(Obj.ToSharedRef(), W);
		return Out;
	}

	bool IsContractVersion(const FString& V)
	{
		// ^0\.[0-9]+$
		if (V.Len() < 3 || V[0] != TEXT('0') || V[1] != TEXT('.')) return false;
		for (int32 I = 2; I < V.Len(); ++I)
		{
			if (V[I] < TEXT('0') || V[I] > TEXT('9')) return false;
		}
		return true;
	}
}

// ----------------------------------------------------------------------------------------------------------------

const TCHAR* AarsCodec::ToString(EAarsPod V) { return EnumName(V, PodNames); }
const TCHAR* AarsCodec::ToString(EAarsStation V) { return EnumName(V, StationNames); }
const TCHAR* AarsCodec::ToString(EAarsReceiverType V) { return EnumName(V, ReceiverTypeNames); }
const TCHAR* AarsCodec::ToString(EAarsPhase V) { return EnumName(V, PhaseNames); }
const TCHAR* AarsCodec::ToString(EAarsAutopilot V) { return EnumName(V, ApNames); }
const TCHAR* AarsCodec::ToString(EAarsLens V) { return EnumName(V, LensNames); }
const TCHAR* AarsCodec::ToString(EAarsReceiverAction V) { return EnumName(V, ActionNames); }
const TCHAR* AarsCodec::ToString(EAarsInboundType V) { return EnumName(V, InboundNames); }

FString AarsCodec::Hello(const FString& Name)
{
	FJsonOut J;
	J.BeginObject();
	J.Str(TEXT("type"), TEXT("hello"));
	J.Str(TEXT("role"), TEXT("world"));
	J.Str(TEXT("name"), Name.Left(64));
	J.Str(TEXT("version"), ContractVersion);
	J.EndObject();
	return J.S;
}

FString AarsCodec::Pong(const FAarsPing& Ping)
{
	FJsonOut J;
	J.BeginObject();
	J.Str(TEXT("type"), TEXT("pong"));
	J.Str(TEXT("id"), Ping.Id);
	J.Int(TEXT("t_ms"), Ping.TMs);
	J.EndObject();
	return J.S;
}

FString AarsCodec::SnapshotReply(const FString& RequestId, int64 TMs, const FString& RestoreJson)
{
	FJsonOut J;
	J.BeginObject();
	J.Str(TEXT("type"), TEXT("snapshot.reply"));
	J.Str(TEXT("request_id"), RequestId);
	J.Int(TEXT("t_ms"), FMath::Max<int64>(0, TMs));
	J.Emit(TEXT("restore"), IsJsonObject(RestoreJson) ? RestoreJson : FString(TEXT("{}")));
	J.EndObject();
	return J.S;
}

FString AarsCodec::WorldState(const FAarsWorldState& St, int64 Seq, TArray<FString>* OutFixes)
{
	FFixer F{ OutFixes };
	FJsonOut J;
	J.BeginObject();
	J.Str(TEXT("type"), TEXT("world.state"));
	J.Int(TEXT("seq"), FMath::Max<int64>(0, Seq));
	J.Int(TEXT("t_ms"), FMath::Max<int64>(0, St.TMs));

	J.BeginObject(TEXT("clock"));
	double Scale = F.Num(TEXT("clock.scale"), St.ClockScale);
	if (Scale <= 0.0)
	{
		if (OutFixes) OutFixes->Add(FString::Printf(TEXT("clock.scale %g -> 1"), Scale));
		Scale = 1.0;
	}
	J.Num(TEXT("scale"), Scale);
	J.Bool(TEXT("paused"), St.bPaused);
	J.EndObject();

	J.BeginObject(TEXT("tanker"));
	J.Num(TEXT("ias_kt"), F.NonNeg(TEXT("tanker.ias_kt"), St.Tanker.IasKt));
	J.Num(TEXT("alt_ft"), F.Num(TEXT("tanker.alt_ft"), St.Tanker.AltFt));
	J.Num(TEXT("bank_deg"), F.Clamp(TEXT("tanker.bank_deg"), St.Tanker.BankDeg, -90.0, 90.0));
	J.Num(TEXT("pitch_deg"), F.Clamp(TEXT("tanker.pitch_deg"), St.Tanker.PitchDeg, -90.0, 90.0));
	J.Num(TEXT("heading_deg"), F.Heading(St.Tanker.HeadingDeg));
	J.Str(TEXT("ap"), ToString(St.Tanker.Ap));
	J.EndObject();

	J.BeginObject(TEXT("pods"));
	WritePod(J, TEXT("LEFT"), St.PodLeft, F);
	WritePod(J, TEXT("RIGHT"), St.PodRight, F);
	J.EndObject();

	const FAarsBoomWorld& B = St.Boom;
	J.BeginObject(TEXT("boom"));
	J.BeginObject(TEXT("tip"));
	J.Num(TEXT("az_deg"), F.Num(TEXT("boom.tip.az_deg"), B.Tip.AzDeg));
	J.Num(TEXT("el_deg"), F.Num(TEXT("boom.tip.el_deg"), B.Tip.ElDeg));
	J.Num(TEXT("tele_ft"), F.NonNeg(TEXT("boom.tip.tele_ft"), B.Tip.TeleFt));
	J.EndObject();
	J.Bool(TEXT("contact"), B.bContact);
	J.IdOrNull(TEXT("receiver_id"), F.Id(TEXT("boom.receiver_id"), B.ReceiverId));
	if (B.bHoleValid)
	{
		J.BeginObject(TEXT("hole"));
		J.Num(TEXT("az_deg"), F.Num(TEXT("boom.hole.az_deg"), B.Hole.AzDeg));
		J.Num(TEXT("el_deg"), F.Num(TEXT("boom.hole.el_deg"), B.Hole.ElDeg));
		J.Num(TEXT("range_ft"), F.NonNeg(TEXT("boom.hole.range_ft"), B.Hole.RangeFt));
		J.Num(TEXT("d_az_dps"), F.Num(TEXT("boom.hole.d_az_dps"), B.Hole.DAzDps));
		J.Num(TEXT("d_el_dps"), F.Num(TEXT("boom.hole.d_el_dps"), B.Hole.DElDps));
		J.Num(TEXT("d_range_fps"), F.Num(TEXT("boom.hole.d_range_fps"), B.Hole.DRangeFps));
		J.EndObject();
	}
	else
	{
		J.Null(TEXT("hole"));
	}
	if (B.bTrackBoxValid)
	{
		J.BeginArray(TEXT("track_box"));
		J.Num(nullptr, F.Clamp(TEXT("boom.track_box.x"), B.TrackX, 0.0, 1.0));
		J.Num(nullptr, F.Clamp(TEXT("boom.track_box.y"), B.TrackY, 0.0, 1.0));
		J.Num(nullptr, F.Clamp(TEXT("boom.track_box.w"), B.TrackW, 0.0, 1.0));
		J.Num(nullptr, F.Clamp(TEXT("boom.track_box.h"), B.TrackH, 0.0, 1.0));
		J.EndArray();
	}
	else
	{
		J.Null(TEXT("track_box"));
	}
	J.EndObject();

	J.BeginArray(TEXT("receivers"));
	for (const FAarsReceiverState& R : St.Receivers)
	{
		FString Id = F.Id(TEXT("receivers.id"), R.Id);
		if (Id.IsEmpty())
		{
			if (OutFixes) OutFixes->Add(TEXT("receiver with empty id skipped"));
			continue;
		}
		J.BeginObject();
		J.Str(TEXT("id"), Id);
		J.Str(TEXT("type"), ToString(R.Type));
		if (R.Behind == EAarsStation::None) J.Null(TEXT("behind"));
		else J.Str(TEXT("behind"), ToString(R.Behind));
		J.Str(TEXT("phase"), ToString(R.Phase));
		J.Num(TEXT("ias_kt"), F.NonNeg(TEXT("receivers.ias_kt"), R.IasKt));
		J.Num(TEXT("alt_ft"), F.Num(TEXT("receivers.alt_ft"), R.AltFt));
		J.Num(TEXT("bank_deg"), F.Clamp(TEXT("receivers.bank_deg"), R.BankDeg, -90.0, 90.0));
		J.EndObject();
	}
	J.EndArray();

	if (!St.RestoreJson.IsEmpty())
	{
		if (IsJsonObject(St.RestoreJson)) J.Emit(TEXT("restore"), St.RestoreJson);
		else if (OutFixes) OutFixes->Add(TEXT("restore is not a JSON object, omitted"));
	}
	J.EndObject();
	return J.S;
}

bool AarsCodec::IsJsonObject(const FString& Text)
{
	TSharedPtr<FJsonObject> Obj;
	TSharedRef<TJsonReader<>> R = TJsonReaderFactory<>::Create(Text);
	return FJsonSerializer::Deserialize(R, Obj) && Obj.IsValid();
}

bool AarsCodec::Parse(const FString& Text, FAarsInbound& Out, FString& Error)
{
	Out = FAarsInbound();
	Error.Reset();

	TSharedPtr<FJsonObject> Obj;
	TSharedRef<TJsonReader<>> JR = TJsonReaderFactory<>::Create(Text);
	if (!FJsonSerializer::Deserialize(JR, Obj) || !Obj.IsValid())
	{
		Error = TEXT("not a JSON object");
		return false;
	}

	FReader R(Obj, TEXT("$"), Error);
	FString Type;
	if (!R.String(TEXT("type"), Type)) return false;

	if (Type == TEXT("hello"))
	{
		FAarsHello& M = Out.Hello;
		FString Role;
		if (!R.String(TEXT("role"), Role)) return false;
		if (Role != TEXT("sim") && Role != TEXT("world")) return R.Fail(TEXT("role"), FString::Printf(TEXT("'%s' is not one of sim, world"), *Role));
		if (!R.String(TEXT("name"), M.Name, 0, 64) || !R.String(TEXT("version"), M.Version)) return false;
		if (!IsContractVersion(M.Version)) return R.Fail(TEXT("version"), FString::Printf(TEXT("'%s' does not match ^0\\.[0-9]+$"), *M.Version));
		M.Role = Role;
		Out.Type = EAarsInboundType::Hello;
	}
	else if (Type == TEXT("ping"))
	{
		if (!R.Id(TEXT("id"), Out.Ping.Id) || !R.Integer(TEXT("t_ms"), Out.Ping.TMs)) return false;
		Out.Type = EAarsInboundType::Ping;
	}
	else if (Type == TEXT("pod.hose"))
	{
		FAarsPodHose& M = Out.PodHose;
		if (!R.Integer(TEXT("seq"), M.Seq) || !R.Integer(TEXT("t_ms"), M.TMs) || !R.Enum(TEXT("pod"), M.Pod, PodNames)
			|| !R.Number(TEXT("payout_ft"), M.PayoutFt, 0.0) || !R.Bool(TEXT("attached"), M.bAttached) || !R.Bool(TEXT("cut"), M.bCut)) return false;
		Out.Type = EAarsInboundType::PodHose;
	}
	else if (Type == TEXT("pod.fluid"))
	{
		FAarsPodFluid& M = Out.PodFluid;
		if (!R.Enum(TEXT("pod"), M.Pod, PodNames) || !R.Number(TEXT("fuel_pressure_psi"), M.FuelPressurePsi, 0.0)
			|| !R.Number(TEXT("flow_lb_min"), M.FlowLbMin, 0.0)) return false;
		Out.Type = EAarsInboundType::PodFluid;
	}
	else if (Type == TEXT("boom.drive"))
	{
		FAarsBoomDrive& M = Out.BoomDrive;
		if (!R.Integer(TEXT("seq"), M.Seq) || !R.Integer(TEXT("t_ms"), M.TMs) || !R.Number(TEXT("el_deg"), M.ElDeg)
			|| !R.Number(TEXT("az_deg"), M.AzDeg) || !R.Number(TEXT("tele_ft"), M.TeleFt, 0.0) || !R.Bool(TEXT("attached"), M.bAttached)) return false;
		Out.Type = EAarsInboundType::BoomDrive;
	}
	else if (Type == TEXT("boom.fluid"))
	{
		FAarsBoomFluid& M = Out.BoomFluid;
		if (!R.Number(TEXT("fuel_pressure_psi"), M.FuelPressurePsi, 0.0) || !R.Number(TEXT("flow_lb_min"), M.FlowLbMin, 0.0)) return false;
		Out.Type = EAarsInboundType::BoomFluid;
	}
	else if (Type == TEXT("camera.lens"))
	{
		if (!R.Enum(TEXT("pod"), Out.CameraLens.Pod, PodNames) || !R.Enum(TEXT("lens"), Out.CameraLens.Lens, LensNames)) return false;
		Out.Type = EAarsInboundType::CameraLens;
	}
	else if (Type == TEXT("camera.select")) // proposed extension, not in contract 0.2
	{
		if (!R.Enum(TEXT("pod"), Out.CameraSelect.Pod, PodNames)) return false;
		Out.Type = EAarsInboundType::CameraSelect;
	}
	else if (Type == TEXT("clock.set"))
	{
		if (!R.Number(TEXT("scale"), Out.ClockSet.Scale, 0.0, 100.0, true, false) || !R.Bool(TEXT("paused"), Out.ClockSet.bPaused)) return false;
		Out.Type = EAarsInboundType::ClockSet;
	}
	else if (Type == TEXT("snapshot.request"))
	{
		if (!R.Id(TEXT("request_id"), Out.SnapshotRequest.RequestId)) return false;
		Out.Type = EAarsInboundType::SnapshotRequest;
	}
	else if (Type == TEXT("world.set"))
	{
		TSharedPtr<FJsonObject> Restore;
		if (!R.Integer(TEXT("t_ms"), Out.WorldSet.TMs) || !R.Object(TEXT("restore"), Restore)) return false;
		Out.WorldSet.RestoreJson = ToCondensed(Restore);
		Out.Type = EAarsInboundType::WorldSet;
	}
	else if (Type == TEXT("world.resume"))
	{
		Out.Type = EAarsInboundType::WorldResume;
	}
	else if (Type == TEXT("tanker.set"))
	{
		FAarsTankerSet& M = Out.TankerSet;
		if (R.NumFields() < 2) return R.Fail(TEXT(""), TEXT("tanker.set needs at least one field besides type"));
		M.bHasIasKt = R.Has(TEXT("ias_kt"));
		M.bHasAltFt = R.Has(TEXT("alt_ft"));
		M.bHasBankDeg = R.Has(TEXT("bank_deg"));
		M.bHasAp = R.Has(TEXT("ap"));
		if (!R.Number(TEXT("ias_kt"), M.IasKt, 0.0, TNumericLimits<double>::Max(), false, false, false)
			|| !R.Number(TEXT("alt_ft"), M.AltFt, -TNumericLimits<double>::Max(), TNumericLimits<double>::Max(), false, false, false)
			|| !R.Number(TEXT("bank_deg"), M.BankDeg, -90.0, 90.0, false, false, false)
			|| !R.Enum(TEXT("ap"), M.Ap, ApNames, 0, false)) return false;
		Out.Type = EAarsInboundType::TankerSet;
	}
	else if (Type == TEXT("receiver.add"))
	{
		FAarsReceiverAdd& M = Out.ReceiverAdd;
		if (!R.Id(TEXT("id"), M.Id) || !R.Enum(TEXT("receiver_type"), M.ReceiverType, ReceiverTypeNames)
			|| !R.Enum(TEXT("behind"), M.Behind, StationNames, 1)) return false;
		Out.Type = EAarsInboundType::ReceiverAdd;
	}
	else if (Type == TEXT("receiver.command"))
	{
		if (!R.Id(TEXT("id"), Out.ReceiverCommand.Id) || !R.Enum(TEXT("action"), Out.ReceiverCommand.Action, ActionNames)) return false;
		Out.Type = EAarsInboundType::ReceiverCommand;
	}
	else if (Type == TEXT("receiver.remove"))
	{
		if (!R.Id(TEXT("id"), Out.ReceiverRemove.Id)) return false;
		Out.Type = EAarsInboundType::ReceiverRemove;
	}
	else if (Type == TEXT("pong") || Type == TEXT("world.state") || Type == TEXT("snapshot.reply"))
	{
		return R.Fail(TEXT("type"), FString::Printf(TEXT("'%s' is sent by the World, not to it"), *Type));
	}
	else
	{
		return R.Fail(TEXT("type"), FString::Printf(TEXT("unknown message type '%s'"), *Type));
	}

	if (!R.NoOtherFields())
	{
		Out.Type = EAarsInboundType::None;
		return false;
	}
	return true;
}
