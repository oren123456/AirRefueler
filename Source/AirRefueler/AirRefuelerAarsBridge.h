// Connects the AirRefueler scene to the AARS link (AarsLink plugin):
//  - world.state: right/left pod from BP_RefuelHose (tip_ft, contact), the player's Mirage as receiver "PLAYER",
//    tanker from Project Settings > AARS Link (the tanker does not fly), no boom;
//  - snapshot.request / world.set: player pose + hose state ("airrefueler/1" restore).
//  - pod.hose drives the hose (contract: the Simulator owns the drum): payout_ft = trailed length, 0 = stowed,
//    attached = the drum yields up to the full length, cut = hose and drogue gone. A latched probe is released when the
//    hose would have to stretch more than 1 ft past its limit. Until the first pod.hose, the hose runs locally (E key).
//  - video: ONE stream (Pixel Streaming 2) showing ONE pod camera; the player's viewport stays in the cockpit.
//    One CineCamera per pod looks aft at the drogue (a level CineCameraActor labelled PodCam_Left / PodCam_Right is used
//    if present, otherwise one is spawned at the pod). A single off-screen SceneCapture (1920x1080) sits on the
//    selected pod camera; its render target replaces the video of the Pixel Streaming default streamer.
//    camera.select {pod} (proposed extension, not in contract 0.2) picks the pod; camera.lens sets a pod's lens
//    (WIDE 12 mm / NARROW 50 mm). Testing: keys 1 = left pod, 2 = right pod, N = toggle the selected pod's lens;
//    console "aars.Camera Left|Right", "aars.Lens Left|Right Wide|Narrow".
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
	/** Pod camera lenses (placeholders until AARS gives the real FOVs): focal length in mm on a 23.76 mm wide sensor.
	 *  WIDE 12 mm = 89 deg horizontal, NARROW 50 mm = 27 deg. */
	static constexpr float WideFocalMm = 12.f;
	static constexpr float NarrowFocalMm = 50.f;

	/** Stream resolution (16:9, like the pod camera sensor). */
	static constexpr int32 StreamWidth = 1920;
	static constexpr int32 StreamHeight = 1080;

	/** Put this pod's camera on the video stream (camera.select). */
	void SelectCamera(EAarsPod Pod);
	EAarsPod GetSelectedPod() const { return SelectedPod; }
	void SetLens(EAarsPod Pod, EAarsLens Lens);
	/** The bridge of the running game / PIE world (for console commands). */
	static UAirRefuelerAarsBridge* FindRunning();

private:
	void FillWorldState(FAarsWorldState& State);
	FString MakeRestore() const;
	bool ApplyRestore(const FString& Json);
	void FindHoses();
	virtual void Deinitialize() override;
	void SetupPodCameras();
	void SetupStream();
	void FeedStreamer();
	void ReleaseStream();
	void PollKeys();
	UFUNCTION()
	void HandleCameraLens(const FAarsCameraLens& Message);
	UFUNCTION()
	void HandleCameraSelect(const FAarsCameraSelect& Message);

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

	struct FPodCamera
	{
		TWeakObjectPtr<class ACineCameraActor> Camera;
		EAarsPod Pod = EAarsPod::Right;
		EAarsLens Lens = EAarsLens::Wide;
		bool bSpawned = false;
	};
	FPodCamera* FindCamera(EAarsPod Pod);
	TArray<FPodCamera> PodCameras;
	EAarsPod SelectedPod = EAarsPod::Right; // the player's Mirage starts behind the right pod

	// The one video stream: an off-screen capture on the selected pod camera -> render target -> Pixel Streaming.
	UPROPERTY(Transient)
	TObjectPtr<class UTextureRenderTarget2D> StreamTarget;
	UPROPERTY(Transient)
	TObjectPtr<class ASceneCapture2D> StreamCapture;
	TSharedPtr<class IPixelStreaming2VideoProducer> StreamProducer;
	bool bLoggedStreamer = false;
	TWeakObjectPtr<class UAarsLinkSubsystem> Link;
};
