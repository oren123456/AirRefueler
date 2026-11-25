// World side of the AARS link: WebSocket server (Unreal's WebSocketNetworking plugin) + contract codec.
//
// Per frame, on the game thread:
//   Link.Receive();                 // services the socket; fires the On* events for what the Simulator sent
//   ... update the World ...
//   Link.SendWorldState(State);     // 60 Hz
//   Link.Flush();                   // the plugin writes one message per service call: this drains the queue
//
// Plugin facts this class works around (measured, see AarsWsTest/README.md):
//  - outbound frames are always binary (payload = UTF-8 JSON); inbound must be TEXT frames (binary ones are lost);
//  - one message written per service call -> Flush() services once per queued message;
//  - a connection cannot be closed from the server: a newer connection replaces the old one, which is then ignored,
//    and a Simulator with the wrong contract version is ignored (not closed) until it sends a matching hello.
#pragma once

#include "CoreMinimal.h"
#include "AarsTypes.h"

class INetworkingWebSocket;
class IWebSocketServer;

class AARSLINK_API FAarsLinkServer
{
public:
	struct FStats
	{
		int64 Connects = 0;
		int64 Disconnects = 0;
		int64 Replaced = 0;          // connections superseded by a newer one
		int64 Received = 0;          // messages from the active connection
		int64 Accepted = 0;
		int64 Rejected = 0;          // broke the contract (see LastRejects)
		int64 Stale = 0;             // pod.hose / boom.drive with a seq not newer than the last one
		int64 IgnoredInactive = 0;   // from a superseded connection
		int64 IgnoredVersion = 0;    // after a hello with another contract version
		int64 Sent = 0;
		int64 NotConnectedDrops = 0; // Send* with no Simulator connected
		int64 Fixes = 0;             // world.state values made legal by the codec
		TMap<EAarsInboundType, int64> ByType;
		TArray<FString> LastRejects; // newest last, at most 20
		TArray<FString> LastFixes;   // newest last, at most 20
		FString PeerName;
		FString PeerVersion;
		bool bVersionMismatch = false;
	};

	FAarsLinkServer();
	~FAarsLinkServer();

	/** Listen on Port. BindAddress empty = all interfaces (the Simulator runs on another PC). */
	bool Start(int32 Port, const FString& BindAddress = FString(), const FString& WorldName = TEXT("unreal"));
	void Stop();
	bool IsRunning() const;
	bool IsConnected() const { return Active != nullptr; }

	/** Once per frame, before using the World's inputs. */
	void Receive();
	/** Once per frame, after this frame's Send* calls. */
	void Flush();

	void SendWorldState(const FAarsWorldState& State);
	void SendSnapshotReply(const FString& RequestId, int64 TMs, const FString& RestoreJson);

	/** Answer ping with pong inside Receive() (default true). */
	bool bAutoPong = true;
	/** Drop pod.hose / boom.drive whose seq is not newer than the last one of the same stream (default true). */
	bool bDropStale = true;

	TMulticastDelegate<void()> OnConnected;
	TMulticastDelegate<void()> OnDisconnected;
	TMulticastDelegate<void(const FAarsHello&)> OnHello;
	TMulticastDelegate<void(const FAarsPing&)> OnPing;
	TMulticastDelegate<void(const FAarsPodHose&)> OnPodHose;
	TMulticastDelegate<void(const FAarsPodFluid&)> OnPodFluid;
	TMulticastDelegate<void(const FAarsBoomDrive&)> OnBoomDrive;
	TMulticastDelegate<void(const FAarsBoomFluid&)> OnBoomFluid;
	TMulticastDelegate<void(const FAarsCameraLens&)> OnCameraLens;
	TMulticastDelegate<void(const FAarsClockSet&)> OnClockSet;
	TMulticastDelegate<void(const FAarsSnapshotRequest&)> OnSnapshotRequest;
	TMulticastDelegate<void(const FAarsWorldSet&)> OnWorldSet;
	TMulticastDelegate<void()> OnWorldResume;
	TMulticastDelegate<void(const FAarsTankerSet&)> OnTankerSet;
	TMulticastDelegate<void(const FAarsReceiverAdd&)> OnReceiverAdd;
	TMulticastDelegate<void(const FAarsReceiverCommand&)> OnReceiverCommand;
	TMulticastDelegate<void(const FAarsReceiverRemove&)> OnReceiverRemove;
	/** (raw message, reason) for anything that broke the contract. */
	TMulticastDelegate<void(const FString&, const FString&)> OnRejected;

	const FStats& GetStats() const { return Stats; }

private:
	void HandleConnected(INetworkingWebSocket* Socket);
	void HandleReceived(INetworkingWebSocket* From, void* Data, int32 Size);
	void HandleClosed(INetworkingWebSocket* Socket);
	void Dispatch(const FAarsInbound& Msg);
	void SendText(const FString& Json);
	void Reject(const FString& Raw, const FString& Why);

	TUniquePtr<IWebSocketServer> Server;
	INetworkingWebSocket* Active = nullptr;
	FString WorldName;
	int64 WorldStateSeq = 0;
	int32 QueuedSinceFlush = 0;
	TMap<FString, int64> LastSeq;
	FStats Stats;
};
