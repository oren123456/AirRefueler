#include "AarsLinkServer.h"

#include "AarsCodec.h"
#include "AarsLinkLog.h"
#include "INetworkingWebSocket.h"
#include "IWebSocketNetworkingModule.h"
#include "IWebSocketServer.h"
#include "IPAddress.h"
#include "Modules/ModuleManager.h"
#include "SocketSubsystem.h"
#include "Sockets.h"

namespace
{
	/**
	 * The plugin listens with SO_REUSEADDR (LWS_SERVER_OPTION_ALLOW_LISTEN_SHARE), so Init() succeeds even when another
	 * program already listens on the port, and the Simulator may then reach that program instead. Bind a plain socket
	 * first to find out.
	 */
	bool IsPortFree(int32 Port, const FString& BindAddress, FString& Why)
	{
		ISocketSubsystem* SS = ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM);
		if (!SS) return true;
		TSharedRef<FInternetAddr> Addr = SS->CreateInternetAddr();
		if (BindAddress.IsEmpty())
		{
			Addr->SetAnyAddress();
		}
		else
		{
			bool bValid = false;
			Addr->SetIp(*BindAddress, bValid);
			if (!bValid)
			{
				Why = FString::Printf(TEXT("'%s' is not an IP address"), *BindAddress);
				return false;
			}
		}
		Addr->SetPort(Port);
		FSocket* Probe = SS->CreateSocket(NAME_Stream, TEXT("AarsLinkPortProbe"), Addr->GetProtocolType());
		if (!Probe) return true;
		Probe->SetReuseAddr(false);
		const bool bFree = Probe->Bind(*Addr);
		if (!bFree) Why = TEXT("another program is already listening on it");
		Probe->Close();
		SS->DestroySocket(Probe);
		return bFree;
	}
}

FAarsLinkServer::FAarsLinkServer() = default;

FAarsLinkServer::~FAarsLinkServer()
{
	Stop();
}

bool FAarsLinkServer::Start(int32 Port, const FString& BindAddress, const FString& InWorldName)
{
	Stop();
	WorldName = InWorldName;
	FString Why;
	if (!IsPortFree(Port, BindAddress, Why))
	{
		UE_LOG(LogAarsLink, Error, TEXT("AARS link: cannot use port %d: %s"), Port, *Why);
		return false;
	}
	IWebSocketNetworkingModule& Module = FModuleManager::LoadModuleChecked<IWebSocketNetworkingModule>(TEXT("WebSocketNetworking"));
	Server = Module.CreateServer();
	if (!Server.IsValid()) return false;

	const bool bOk = Server->Init((uint32)Port, FWebSocketClientConnectedCallBack::CreateRaw(this, &FAarsLinkServer::HandleConnected), BindAddress);
	if (!bOk)
	{
		UE_LOG(LogAarsLink, Error, TEXT("AARS link: cannot listen on port %d (%s)"), Port, BindAddress.IsEmpty() ? TEXT("all interfaces") : *BindAddress);
		Server.Reset();
		return false;
	}
	UE_LOG(LogAarsLink, Display, TEXT("AARS link: listening on %s:%d, contract %s"), BindAddress.IsEmpty() ? TEXT("*") : *BindAddress, Port, AarsCodec::ContractVersion);
	return true;
}

void FAarsLinkServer::Stop()
{
	Active = nullptr;
	Server.Reset();
}

bool FAarsLinkServer::IsRunning() const
{
	return Server.IsValid();
}

void FAarsLinkServer::Receive()
{
	if (Server) Server->Tick();
}

void FAarsLinkServer::Flush()
{
	if (!Server) return;
	// One write per service call; +1 so a write requested by Receive() is not left behind.
	const int32 Ticks = FMath::Clamp(QueuedSinceFlush + 1, 1, 256);
	for (int32 I = 0; I < Ticks; ++I) Server->Tick();
	QueuedSinceFlush = 0;
}

void FAarsLinkServer::HandleConnected(INetworkingWebSocket* Socket)
{
	if (Active)
	{
		++Stats.Replaced;
		UE_LOG(LogAarsLink, Warning, TEXT("AARS link: new connection from %s replaces the previous one"), *Socket->RemoteEndPoint(true));
	}
	Active = Socket;
	++Stats.Connects;
	Stats.bVersionMismatch = false;
	Stats.PeerName.Reset();
	Stats.PeerVersion.Reset();
	LastSeq.Reset();

	Socket->SetReceiveCallBack(FWebSocketPacketReceivedCallBack::CreateLambda([this, Socket](void* Data, int32 Size) { HandleReceived(Socket, Data, Size); }));
	Socket->SetSocketClosedCallBack(FWebSocketInfoCallBack::CreateLambda([this, Socket]() { HandleClosed(Socket); }));

	UE_LOG(LogAarsLink, Display, TEXT("AARS link: Simulator connected from %s"), *Socket->RemoteEndPoint(true));
	SendText(AarsCodec::Hello(WorldName));
	OnConnected.Broadcast();
}

void FAarsLinkServer::HandleClosed(INetworkingWebSocket* Socket)
{
	if (Socket != Active) return;
	Active = nullptr;
	++Stats.Disconnects;
	UE_LOG(LogAarsLink, Display, TEXT("AARS link: Simulator disconnected (the World keeps running)"));
	OnDisconnected.Broadcast();
}

void FAarsLinkServer::Reject(const FString& Raw, const FString& Why)
{
	++Stats.Rejected;
	if (Stats.LastRejects.Num() >= 20) Stats.LastRejects.RemoveAt(0);
	Stats.LastRejects.Add(Why + TEXT("  <-  ") + Raw.Left(200));
	UE_LOG(LogAarsLink, Warning, TEXT("AARS link: rejected message: %s"), *Why);
	OnRejected.Broadcast(Raw, Why);
}

void FAarsLinkServer::HandleReceived(INetworkingWebSocket* From, void* Data, int32 Size)
{
	if (From != Active)
	{
		++Stats.IgnoredInactive;
		return;
	}
	++Stats.Received;

	FUTF8ToTCHAR Conv((const ANSICHAR*)Data, Size);
	const FString Text(Conv.Length(), Conv.Get());

	FAarsInbound Msg;
	FString Error;
	if (!AarsCodec::Parse(Text, Msg, Error))
	{
		Reject(Text, Error);
		return;
	}

	if (Msg.Type == EAarsInboundType::Hello)
	{
		Stats.PeerName = Msg.Hello.Name;
		Stats.PeerVersion = Msg.Hello.Version;
		if (Msg.Hello.Role != TEXT("sim"))
		{
			Reject(Text, FString::Printf(TEXT("hello.role is '%s', expected 'sim'"), *Msg.Hello.Role));
			return;
		}
		Stats.bVersionMismatch = Msg.Hello.Version != AarsCodec::ContractVersion;
		if (Stats.bVersionMismatch)
		{
			UE_LOG(LogAarsLink, Error, TEXT("AARS link: Simulator '%s' speaks contract %s, World speaks %s: ignoring it until a matching hello"),
				*Msg.Hello.Name, *Msg.Hello.Version, AarsCodec::ContractVersion);
		}
		else
		{
			UE_LOG(LogAarsLink, Display, TEXT("AARS link: hello from '%s', contract %s"), *Msg.Hello.Name, *Msg.Hello.Version);
		}
	}
	else if (Stats.bVersionMismatch)
	{
		++Stats.IgnoredVersion;
		return;
	}

	if (bDropStale && (Msg.Type == EAarsInboundType::PodHose || Msg.Type == EAarsInboundType::BoomDrive))
	{
		const FString Stream = Msg.Type == EAarsInboundType::PodHose ? FString(TEXT("pod.hose/")) + AarsCodec::ToString(Msg.PodHose.Pod) : FString(TEXT("boom.drive"));
		const int64 Seq = Msg.Type == EAarsInboundType::PodHose ? Msg.PodHose.Seq : Msg.BoomDrive.Seq;
		if (const int64* Last = LastSeq.Find(Stream))
		{
			if (Seq <= *Last)
			{
				++Stats.Stale;
				return;
			}
		}
		LastSeq.Add(Stream, Seq);
	}

	++Stats.Accepted;
	Stats.ByType.FindOrAdd(Msg.Type)++;
	Dispatch(Msg);
}

void FAarsLinkServer::Dispatch(const FAarsInbound& M)
{
	switch (M.Type)
	{
	case EAarsInboundType::Hello: OnHello.Broadcast(M.Hello); break;
	case EAarsInboundType::Ping:
		if (bAutoPong) SendText(AarsCodec::Pong(M.Ping));
		OnPing.Broadcast(M.Ping);
		break;
	case EAarsInboundType::PodHose: OnPodHose.Broadcast(M.PodHose); break;
	case EAarsInboundType::PodFluid: OnPodFluid.Broadcast(M.PodFluid); break;
	case EAarsInboundType::BoomDrive: OnBoomDrive.Broadcast(M.BoomDrive); break;
	case EAarsInboundType::BoomFluid: OnBoomFluid.Broadcast(M.BoomFluid); break;
	case EAarsInboundType::CameraLens: OnCameraLens.Broadcast(M.CameraLens); break;
	case EAarsInboundType::CameraSelect: OnCameraSelect.Broadcast(M.CameraSelect); break;
	case EAarsInboundType::ClockSet: OnClockSet.Broadcast(M.ClockSet); break;
	case EAarsInboundType::SnapshotRequest: OnSnapshotRequest.Broadcast(M.SnapshotRequest); break;
	case EAarsInboundType::WorldSet: OnWorldSet.Broadcast(M.WorldSet); break;
	case EAarsInboundType::WorldResume: OnWorldResume.Broadcast(); break;
	case EAarsInboundType::TankerSet: OnTankerSet.Broadcast(M.TankerSet); break;
	case EAarsInboundType::ReceiverAdd: OnReceiverAdd.Broadcast(M.ReceiverAdd); break;
	case EAarsInboundType::ReceiverCommand: OnReceiverCommand.Broadcast(M.ReceiverCommand); break;
	case EAarsInboundType::ReceiverRemove: OnReceiverRemove.Broadcast(M.ReceiverRemove); break;
	default: break;
	}
}

void FAarsLinkServer::SendText(const FString& Json)
{
	if (!Active)
	{
		++Stats.NotConnectedDrops;
		return;
	}
	FTCHARToUTF8 Utf8(*Json);
	// bPrependSize = false: otherwise the plugin puts a 4-byte length in front of the JSON.
	Active->Send((const uint8*)Utf8.Get(), Utf8.Length(), false);
	++Stats.Sent;
	++QueuedSinceFlush;
}

void FAarsLinkServer::SendWorldState(const FAarsWorldState& State)
{
	if (!Active)
	{
		++Stats.NotConnectedDrops;
		return;
	}
	TArray<FString> Fixes;
	SendText(AarsCodec::WorldState(State, WorldStateSeq++, &Fixes));
	if (Fixes.Num() > 0)
	{
		Stats.Fixes += Fixes.Num();
		for (const FString& F : Fixes)
		{
			if (Stats.LastFixes.Num() >= 20) Stats.LastFixes.RemoveAt(0);
			Stats.LastFixes.Add(F);
		}
	}
}

void FAarsLinkServer::SendSnapshotReply(const FString& RequestId, int64 TMs, const FString& RestoreJson)
{
	SendText(AarsCodec::SnapshotReply(RequestId, TMs, RestoreJson));
}
