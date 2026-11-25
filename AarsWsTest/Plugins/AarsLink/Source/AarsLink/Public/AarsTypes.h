// Messages of the AARS <-> World contract, version 0.2 (DRAFT).
// Binding definition: AARS-world-contract-0.2/schema/messages.schema.json.
// Units are the contract's (feet, knots, degrees, pounds, psi, milliseconds); field names keep the unit suffix.
#pragma once

#include "CoreMinimal.h"
#include "AarsTypes.generated.h"

UENUM(BlueprintType)
enum class EAarsPod : uint8 { Left, Right };

/** Station a receiver is behind. None = JSON null (only allowed in world.state receivers[].behind). */
UENUM(BlueprintType)
enum class EAarsStation : uint8 { None, Left, Right, Boom };

UENUM(BlueprintType)
enum class EAarsReceiverType : uint8 { Rafale, FA18 UMETA(DisplayName = "F/A-18"), C130 UMETA(DisplayName = "C-130"), F35 UMETA(DisplayName = "F-35"), F16 UMETA(DisplayName = "F-16"), Other };

UENUM(BlueprintType)
enum class EAarsPhase : uint8 { Free, Approach, Astern, Contact, Departing };

UENUM(BlueprintType)
enum class EAarsAutopilot : uint8 { Cmd, Off };

UENUM(BlueprintType)
enum class EAarsLens : uint8 { Wide, Narrow };

UENUM(BlueprintType)
enum class EAarsReceiverAction : uint8 { Approach, Astern, Contact, Disconnect, Breakaway, Leave };

/** Message types the World receives from the Simulator. */
UENUM(BlueprintType)
enum class EAarsInboundType : uint8
{
	None, Hello, Ping, PodHose, PodFluid, BoomDrive, BoomFluid, CameraLens, ClockSet,
	SnapshotRequest, WorldSet, WorldResume, TankerSet, ReceiverAdd, ReceiverCommand, ReceiverRemove
};

// ---------------------------------------------------------------------------------------------------------------
// World -> Simulator: world.state

USTRUCT(BlueprintType)
struct AARSLINK_API FAarsTanker
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") double IasKt = 0.0;      // >= 0
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") double AltFt = 0.0;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") double BankDeg = 0.0;    // -90..90
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") double PitchDeg = 0.0;   // -90..90
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") double HeadingDeg = 0.0; // [0, 360)
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") EAarsAutopilot Ap = EAarsAutopilot::Cmd;
};

USTRUCT(BlueprintType)
struct AARSLINK_API FAarsPodWorld
{
	GENERATED_BODY()
	/** Distance of the drogue from the pod as the World has it (= payout_ft while nothing touches the drogue). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") double TipFt = 0.0;
	/** A receiver probe is in the drogue (geometric fact). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") bool bContact = false;
	/** Empty = null. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") FString ReceiverId;
};

USTRUCT(BlueprintType)
struct AARSLINK_API FAarsBoomTip
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") double AzDeg = 0.0;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") double ElDeg = 0.0;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") double TeleFt = 0.0; // >= 0
};

/** Receptacle seen from the boom pivot, in the boom's own angles and length, plus rates. */
USTRUCT(BlueprintType)
struct AARSLINK_API FAarsHole
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") double AzDeg = 0.0;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") double ElDeg = 0.0;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") double RangeFt = 0.0; // >= 0
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") double DAzDps = 0.0;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") double DElDps = 0.0;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") double DRangeFps = 0.0;
};

USTRUCT(BlueprintType)
struct AARSLINK_API FAarsBoomWorld
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") FAarsBoomTip Tip;
	/** Nozzle seated in the receptacle (geometric fact). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") bool bContact = false;
	/** Empty = null. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") FString ReceiverId;
	/** false = hole: null (no receiver assigned, or out of view -> Simulator sets LOST). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") bool bHoleValid = false;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") FAarsHole Hole;
	/** false = track_box: null. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") bool bTrackBoxValid = false;
	/** [x, y, w, h] of the receiver in the boom camera image, each 0..1. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") double TrackX = 0.0;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") double TrackY = 0.0;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") double TrackW = 0.0;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") double TrackH = 0.0;
};

USTRUCT(BlueprintType)
struct AARSLINK_API FAarsReceiverState
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") FString Id; // 1..32 chars
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") EAarsReceiverType Type = EAarsReceiverType::Other;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") EAarsStation Behind = EAarsStation::None;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") EAarsPhase Phase = EAarsPhase::Free;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") double IasKt = 0.0;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") double AltFt = 0.0;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") double BankDeg = 0.0;
};

/** world.state, sent at 60 Hz. seq is filled in by the server. */
USTRUCT(BlueprintType)
struct AARSLINK_API FAarsWorldState
{
	GENERATED_BODY()
	/** World clock, ms since the scenario started. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") int64 TMs = 0;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") double ClockScale = 1.0; // > 0
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") bool bPaused = false;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") FAarsTanker Tanker;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") FAarsPodWorld PodLeft;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") FAarsPodWorld PodRight;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") FAarsBoomWorld Boom;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") TArray<FAarsReceiverState> Receivers;
	/** Optional opaque restore object (a JSON object as text). Empty = omitted. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AARS") FString RestoreJson;
};

// ---------------------------------------------------------------------------------------------------------------
// Simulator -> World

USTRUCT(BlueprintType)
struct AARSLINK_API FAarsHello
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "AARS") FString Role;    // "sim" | "world"
	UPROPERTY(BlueprintReadOnly, Category = "AARS") FString Name;
	UPROPERTY(BlueprintReadOnly, Category = "AARS") FString Version; // "0.N"
};

USTRUCT(BlueprintType)
struct AARSLINK_API FAarsPing
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "AARS") FString Id;
	UPROPERTY(BlueprintReadOnly, Category = "AARS") int64 TMs = 0;
};

/** pod.hose, 60 Hz per pod. */
USTRUCT(BlueprintType)
struct AARSLINK_API FAarsPodHose
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "AARS") int64 Seq = 0;
	UPROPERTY(BlueprintReadOnly, Category = "AARS") int64 TMs = 0;
	UPROPERTY(BlueprintReadOnly, Category = "AARS") EAarsPod Pod = EAarsPod::Left;
	/** Hose released by the drum. 0 = stowed. While not attached, the longest the hose can get. */
	UPROPERTY(BlueprintReadOnly, Category = "AARS") double PayoutFt = 0.0;
	/** Simulator decided the receiver is connected: the drum yields up to full length. */
	UPROPERTY(BlueprintReadOnly, Category = "AARS") bool bAttached = false;
	/** Hose cut: hose and drogue separate from the pod for good. */
	UPROPERTY(BlueprintReadOnly, Category = "AARS") bool bCut = false;
};

USTRUCT(BlueprintType)
struct AARSLINK_API FAarsPodFluid
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "AARS") EAarsPod Pod = EAarsPod::Left;
	UPROPERTY(BlueprintReadOnly, Category = "AARS") double FuelPressurePsi = 0.0;
	UPROPERTY(BlueprintReadOnly, Category = "AARS") double FlowLbMin = 0.0;
};

/** boom.drive, 60 Hz. */
USTRUCT(BlueprintType)
struct AARSLINK_API FAarsBoomDrive
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "AARS") int64 Seq = 0;
	UPROPERTY(BlueprintReadOnly, Category = "AARS") int64 TMs = 0;
	/** Boom elevation, hoist included. */
	UPROPERTY(BlueprintReadOnly, Category = "AARS") double ElDeg = 0.0;
	UPROPERTY(BlueprintReadOnly, Category = "AARS") double AzDeg = 0.0;
	UPROPERTY(BlueprintReadOnly, Category = "AARS") double TeleFt = 0.0;
	/** Simulator decided the receiver is coupled: the boom tip moves with the receiver. */
	UPROPERTY(BlueprintReadOnly, Category = "AARS") bool bAttached = false;
};

USTRUCT(BlueprintType)
struct AARSLINK_API FAarsBoomFluid
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "AARS") double FuelPressurePsi = 0.0;
	UPROPERTY(BlueprintReadOnly, Category = "AARS") double FlowLbMin = 0.0;
};

USTRUCT(BlueprintType)
struct AARSLINK_API FAarsCameraLens
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "AARS") EAarsPod Pod = EAarsPod::Left;
	UPROPERTY(BlueprintReadOnly, Category = "AARS") EAarsLens Lens = EAarsLens::Wide;
};

USTRUCT(BlueprintType)
struct AARSLINK_API FAarsClockSet
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "AARS") double Scale = 1.0; // (0, 100]
	UPROPERTY(BlueprintReadOnly, Category = "AARS") bool bPaused = false;
};

USTRUCT(BlueprintType)
struct AARSLINK_API FAarsSnapshotRequest
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "AARS") FString RequestId;
};

USTRUCT(BlueprintType)
struct AARSLINK_API FAarsWorldSet
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "AARS") int64 TMs = 0;
	/** The restore object the World produced earlier, as JSON text. */
	UPROPERTY(BlueprintReadOnly, Category = "AARS") FString RestoreJson;
};

/** tanker.set (demonstrator). Only the fields with bHas* = true were sent. */
USTRUCT(BlueprintType)
struct AARSLINK_API FAarsTankerSet
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "AARS") bool bHasIasKt = false;
	UPROPERTY(BlueprintReadOnly, Category = "AARS") double IasKt = 0.0;
	UPROPERTY(BlueprintReadOnly, Category = "AARS") bool bHasAltFt = false;
	UPROPERTY(BlueprintReadOnly, Category = "AARS") double AltFt = 0.0;
	UPROPERTY(BlueprintReadOnly, Category = "AARS") bool bHasBankDeg = false;
	UPROPERTY(BlueprintReadOnly, Category = "AARS") double BankDeg = 0.0;
	UPROPERTY(BlueprintReadOnly, Category = "AARS") bool bHasAp = false;
	UPROPERTY(BlueprintReadOnly, Category = "AARS") EAarsAutopilot Ap = EAarsAutopilot::Cmd;
};

USTRUCT(BlueprintType)
struct AARSLINK_API FAarsReceiverAdd
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "AARS") FString Id;
	UPROPERTY(BlueprintReadOnly, Category = "AARS") EAarsReceiverType ReceiverType = EAarsReceiverType::Other;
	/** Never None here. */
	UPROPERTY(BlueprintReadOnly, Category = "AARS") EAarsStation Behind = EAarsStation::Left;
};

USTRUCT(BlueprintType)
struct AARSLINK_API FAarsReceiverCommand
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "AARS") FString Id;
	UPROPERTY(BlueprintReadOnly, Category = "AARS") EAarsReceiverAction Action = EAarsReceiverAction::Approach;
};

USTRUCT(BlueprintType)
struct AARSLINK_API FAarsReceiverRemove
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "AARS") FString Id;
};

/** One decoded Simulator -> World message. Only the member matching Type is meaningful. */
struct AARSLINK_API FAarsInbound
{
	EAarsInboundType Type = EAarsInboundType::None;
	FAarsHello Hello;
	FAarsPing Ping;
	FAarsPodHose PodHose;
	FAarsPodFluid PodFluid;
	FAarsBoomDrive BoomDrive;
	FAarsBoomFluid BoomFluid;
	FAarsCameraLens CameraLens;
	FAarsClockSet ClockSet;
	FAarsSnapshotRequest SnapshotRequest;
	FAarsWorldSet WorldSet;
	FAarsTankerSet TankerSet;
	FAarsReceiverAdd ReceiverAdd;
	FAarsReceiverCommand ReceiverCommand;
	FAarsReceiverRemove ReceiverRemove;
};
