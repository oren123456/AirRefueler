// Connects the AirRefueler scene to the AARS link (AarsLink plugin):
//  - world.state: right/left pod from BP_RefuelHose (tip_ft, contact), the player's Mirage as receiver "PLAYER",
//    tanker from Project Settings > AARS Link (the tanker does not fly), no boom;
//  - snapshot.request / world.set: player pose + hose state ("airrefueler/1" restore).
//  - pod.hose drives the hose (contract: the Simulator owns the drum): payout_ft = trailed length, 0 = stowed,
//    attached = the drum yields up to the full length, cut = hose and drogue gone. A latched probe is released when the
//    hose would have to stretch more than 1 ft past its limit. Until the first pod.hose, the hose runs locally (E key).
#pragma once

#include "CoreMinimal.h"
#include "AarsTypes.h"
#include "Subsystems/WorldSubsystem.h"
#include "AirRefuelerAarsBridge.generated.h"

UCLASS()
class UAirRefuelerAarsBridge : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override;
	virtual bool IsTickableWhenPaused() const override { return true; }

	/** Full hose length when the Simulator has the receiver attached (contract parameter, 90 ft). */
	static constexpr double FullHoseFt = 90.0;
	/** Physical disconnect margin past the limit (contract default 1 ft). */
	static constexpr double DisconnectMarginFt = 1.0;

private:
	void FillWorldState(FAarsWorldState& State);
	FString MakeRestore() const;
	bool ApplyRestore(const FString& Json);
	void FindHoses();

	struct FHose
	{
		TWeakObjectPtr<AActor> Actor;
		EAarsPod Pod = EAarsPod::Right;
		// Simulator control
		bool bSimControlled = false;
		bool bCut = false;
		int64 LastSeq = -1;
		double LastPayoutFt = -1.0;
		double LastChangeTime = -100.0;
		bool bExtending = false;
	};
	void DriveHose(FHose& H, const struct FAarsPodHose& M);
	TArray<FHose> Hoses;
	TWeakObjectPtr<class UAarsLinkSubsystem> Link;
};
