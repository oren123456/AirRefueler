// JSON codec for the AARS <-> World contract 0.2.
#pragma once

#include "CoreMinimal.h"
#include "AarsTypes.h"

namespace AarsCodec
{
	/** Contract version this build speaks (hello.version). */
	AARSLINK_API extern const TCHAR* const ContractVersion;

	// ---- World -> Simulator (each returns one JSON object as text) ----
	AARSLINK_API FString Hello(const FString& Name);
	/** pong echoes the ping's id and t_ms unchanged. */
	AARSLINK_API FString Pong(const FAarsPing& Ping);
	/**
	 * world.state. Out-of-contract values are made legal (heading wrapped to [0,360), angles clamped to +-90,
	 * lengths/speeds clamped to >= 0, track box to 0..1, non-finite -> 0, ids cut to 32 chars) and listed in OutFixes.
	 */
	AARSLINK_API FString WorldState(const FAarsWorldState& State, int64 Seq, TArray<FString>* OutFixes = nullptr);
	AARSLINK_API FString SnapshotReply(const FString& RequestId, int64 TMs, const FString& RestoreJson);

	// ---- Simulator -> World ----
	/**
	 * Strict decode of one message against the schema: unknown fields, missing fields, wrong types, bad enum values
	 * and out-of-range numbers are rejected (returns false, Error says where). World-only types are rejected too.
	 */
	AARSLINK_API bool Parse(const FString& Text, FAarsInbound& Out, FString& Error);

	/** true if Text is one JSON object (what "restore" must be). */
	AARSLINK_API bool IsJsonObject(const FString& Text);

	AARSLINK_API const TCHAR* ToString(EAarsPod V);
	AARSLINK_API const TCHAR* ToString(EAarsStation V); // None -> "null"
	AARSLINK_API const TCHAR* ToString(EAarsReceiverType V);
	AARSLINK_API const TCHAR* ToString(EAarsPhase V);
	AARSLINK_API const TCHAR* ToString(EAarsAutopilot V);
	AARSLINK_API const TCHAR* ToString(EAarsLens V);
	AARSLINK_API const TCHAR* ToString(EAarsReceiverAction V);
	AARSLINK_API const TCHAR* ToString(EAarsInboundType V);
}
