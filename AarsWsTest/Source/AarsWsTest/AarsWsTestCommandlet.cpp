#include "AarsWsTestCommandlet.h"

#include "FdProbe.h"
#include "HAL/PlatformProcess.h"
#include "HAL/PlatformTime.h"
#include "INetworkingWebSocket.h"
#include "IWebSocketNetworkingModule.h"
#include "IWebSocketServer.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Modules/ModuleManager.h"
#include "Policies/CondensedJsonPrintPolicy.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

DEFINE_LOG_CATEGORY_STATIC(LogAarsWs, Log, All);

namespace
{
	struct FStat
	{
		TArray<double> V;
		void Add(double X) { V.Add(X); }
		TSharedRef<FJsonObject> ToJson() const
		{
			TSharedRef<FJsonObject> O = MakeShared<FJsonObject>();
			O->SetNumberField(TEXT("n"), V.Num());
			if (V.Num() == 0) return O;
			TArray<double> S = V;
			S.Sort();
			double Sum = 0;
			for (double X : S) Sum += X;
			O->SetNumberField(TEXT("mean"), Sum / S.Num());
			O->SetNumberField(TEXT("p50"), S[S.Num() / 2]);
			O->SetNumberField(TEXT("p99"), S[FMath::Min(S.Num() - 1, (int32)(S.Num() * 0.99))]);
			O->SetNumberField(TEXT("max"), S.Last());
			O->SetNumberField(TEXT("min"), S[0]);
			return O;
		}
	};

	FString Hex(const uint8* Data, int32 Size, int32 Max = 16)
	{
		FString R;
		for (int32 i = 0; i < FMath::Min(Size, Max); ++i) R += FString::Printf(TEXT("%02x "), Data[i]);
		return R.TrimEnd();
	}

	bool SendText(INetworkingWebSocket* S, const FString& Json)
	{
		if (!S) return false;
		FTCHARToUTF8 Utf8(*Json);
		// bPrependSize must be false, otherwise a 4-byte length is put in front of the JSON.
		return S->Send((const uint8*)Utf8.Get(), Utf8.Length(), false);
	}

#define WORLD_STATE_FMT \
		TEXT("{\"type\":\"world.state\",\"seq\":%lld,\"t_ms\":%lld,\"clock\":{\"scale\":1,\"paused\":false},") \
		TEXT("\"tanker\":{\"ias_kt\":250,\"alt_ft\":25000,\"bank_deg\":0,\"pitch_deg\":2.1,\"heading_deg\":90,\"ap\":\"CMD\"},") \
		TEXT("\"pods\":{\"LEFT\":{\"tip_ft\":74,\"contact\":true,\"receiver_id\":\"TIGER1\"},\"RIGHT\":{\"tip_ft\":0,\"contact\":false,\"receiver_id\":null}},") \
		TEXT("\"boom\":{\"tip\":{\"az_deg\":0,\"el_deg\":0,\"tele_ft\":0},\"contact\":false,\"receiver_id\":null,\"hole\":null,\"track_box\":null},") \
		TEXT("\"receivers\":[{\"id\":\"TIGER1\",\"type\":\"RAFALE\",\"behind\":\"LEFT\",\"phase\":\"CONTACT\",\"ias_kt\":250,\"alt_ft\":25000,\"bank_deg\":0.4}]}")
}

UAarsWsTestCommandlet::UAarsWsTestCommandlet()
{
	// IsEditor stays true (default): editor modules load in UnrealEditor-Cmd and assert on GEditor otherwise.
	LogToConsole = true;
}

int32 UAarsWsTestCommandlet::Main(const FString& Params)
{
	int32 Port = 8765, Pre = 1, Post = 0, Hz = 60;
	double Seconds = 20.0;
	FString Mode = TEXT("stream"), OutPath, ReadyPath, Bind = TEXT("127.0.0.1");
	FParse::Value(*Params, TEXT("port="), Port);
	FParse::Value(*Params, TEXT("pre="), Pre);
	FParse::Value(*Params, TEXT("post="), Post);
	FParse::Value(*Params, TEXT("hz="), Hz);
	FParse::Value(*Params, TEXT("seconds="), Seconds);
	FParse::Value(*Params, TEXT("mode="), Mode);
	FParse::Value(*Params, TEXT("out="), OutPath);
	FParse::Value(*Params, TEXT("ready="), ReadyPath);
	FParse::Value(*Params, TEXT("bind="), Bind);

	IWebSocketNetworkingModule& Module = FModuleManager::LoadModuleChecked<IWebSocketNetworkingModule>(TEXT("WebSocketNetworking"));
	TUniquePtr<IWebSocketServer> Server = Module.CreateServer();

	INetworkingWebSocket* Client = nullptr;
	int32 Connects = 0, Disconnects = 0, ConcurrentConnects = 0;
	int32 NoDelay = -3;
	bool bQuit = false;
	int64 RxMsgs = 0, RxBytes = 0, RxBad = 0, PongsQueued = 0, PodHose = 0, PodHoseGaps = 0, LastPodSeq = -1;
	TArray<TSharedPtr<FJsonValue>> RxSamples;
	TMap<FString, int32> RxTypes;
	const double T0 = FPlatformTime::Seconds();
	auto NowMs = [T0]() { return (int64)((FPlatformTime::Seconds() - T0) * 1000.0); };

	auto OnReceive = [&](void* Data, int32 Size)
	{
		++RxMsgs;
		RxBytes += Size;
		const uint8* Bytes = (const uint8*)Data;
		FUTF8ToTCHAR Conv((const ANSICHAR*)Data, Size);
		FString Text(Conv.Length(), Conv.Get());
		TSharedPtr<FJsonObject> Obj;
		TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
		FString Type = TEXT("<unparsed>");
		if (FJsonSerializer::Deserialize(Reader, Obj) && Obj.IsValid())
		{
			Obj->TryGetStringField(TEXT("type"), Type);
		}
		else
		{
			++RxBad;
		}
		RxTypes.FindOrAdd(Type)++;
		if (RxSamples.Num() < 40 && Type != TEXT("pod.hose") && Type != TEXT("ping"))
		{
			TSharedRef<FJsonObject> S = MakeShared<FJsonObject>();
			S->SetStringField(TEXT("type"), Type);
			S->SetNumberField(TEXT("size"), Size);
			S->SetStringField(TEXT("hex"), Hex(Bytes, Size));
			S->SetStringField(TEXT("text"), Text.Left(80));
			RxSamples.Add(MakeShared<FJsonValueObject>(S));
		}
		if (Type == TEXT("ping"))
		{
			FString Id;
			int64 PingT = 0;
			Obj->TryGetStringField(TEXT("id"), Id);
			Obj->TryGetNumberField(TEXT("t_ms"), PingT);
			SendText(Client, FString::Printf(TEXT("{\"type\":\"pong\",\"id\":\"%s\",\"t_ms\":%lld}"), *Id, PingT));
			++PongsQueued;
		}
		else if (Type == TEXT("pod.hose"))
		{
			int64 Seq = -1;
			Obj->TryGetNumberField(TEXT("seq"), Seq);
			if (LastPodSeq >= 0 && Seq != LastPodSeq + 1) ++PodHoseGaps;
			LastPodSeq = Seq;
			++PodHose;
		}
		else if (Type == TEXT("quit"))
		{
			bQuit = true;
		}
		else if (Type == TEXT("echo"))
		{
			SendText(Client, Text);
		}
	};

	const bool bInit = Server->Init(Port, FWebSocketClientConnectedCallBack::CreateLambda([&](INetworkingWebSocket* Socket)
	{
		++Connects;
		if (Client) ++ConcurrentConnects;
		Client = Socket;
		AarsFdProbe::GetNoDelay(Socket, NoDelay);
		UE_LOG(LogAarsWs, Display, TEXT("client connected %s  TCP_NODELAY=%d"), *Socket->RemoteEndPoint(true), NoDelay);
		Socket->SetReceiveCallBack(FWebSocketPacketReceivedCallBack::CreateLambda(OnReceive));
		Socket->SetSocketClosedCallBack(FWebSocketInfoCallBack::CreateLambda([&, Socket]()
		{
			++Disconnects;
			if (Client == Socket) Client = nullptr;
			UE_LOG(LogAarsWs, Display, TEXT("client closed"));
		}));
	}), Bind);

	UE_LOG(LogAarsWs, Display, TEXT("Init(%d) = %d  lws %s  mode=%s pre=%d post=%d"), Port, bInit, *AarsFdProbe::LwsVersion(), *Mode, Pre, Post);
	if (!bInit) return 1;
	if (!ReadyPath.IsEmpty()) FFileHelper::SaveStringToFile(TEXT("ready"), *ReadyPath);

	FStat TickMs, FramePeriodMs, FrameWorkMs, QueueDepth;
	int64 Seq = 0, Frames = 0, StateSent = 0, BurstPairs = 0;
	const double Period = 1.0 / FMath::Max(1, Hz);
	double Next = FPlatformTime::Seconds(), LastFrame = 0.0, LastBurst = 0.0;
	const double End = Next + Seconds;
	int32 FinalQueue = -1;

	auto TimedTick = [&]()
	{
		const double A = FPlatformTime::Seconds();
		Server->Tick();
		TickMs.Add((FPlatformTime::Seconds() - A) * 1000.0);
	};

	while (!bQuit && FPlatformTime::Seconds() < End)
	{
		const double FrameStart = FPlatformTime::Seconds();
		if (LastFrame > 0) FramePeriodMs.Add((FrameStart - LastFrame) * 1000.0);
		LastFrame = FrameStart;

		for (int32 i = 0; i < Pre; ++i) TimedTick();

		if (Client)
		{
			if (Mode == TEXT("stream"))
			{
				SendText(Client, FString::Printf(WORLD_STATE_FMT, Seq++, NowMs()));
				++StateSent;
			}
			else if (Mode == TEXT("nagle") && FrameStart - LastBurst >= 0.5)
			{
				LastBurst = FrameStart;
				SendText(Client, FString::Printf(TEXT("{\"type\":\"burst\",\"n\":%lld,\"part\":\"A\"}"), BurstPairs));
				SendText(Client, FString::Printf(TEXT("{\"type\":\"burst\",\"n\":%lld,\"part\":\"B\"}"), BurstPairs));
				++BurstPairs;
			}
		}

		for (int32 i = 0; i < Post; ++i) TimedTick();

		int32 Depth = -1;
		if (Client && AarsFdProbe::GetQueueDepth(Client, Depth)) { QueueDepth.Add(Depth); FinalQueue = Depth; }

		FrameWorkMs.Add((FPlatformTime::Seconds() - FrameStart) * 1000.0);
		++Frames;

		Next += Period;
		for (;;)
		{
			const double Rem = Next - FPlatformTime::Seconds();
			if (Rem <= 0) break;
			FPlatformProcess::SleepNoStats(Rem > 0.002 ? (float)(Rem - 0.0015) : 0.0f);
		}
	}

	TSharedRef<FJsonObject> R = MakeShared<FJsonObject>();
	R->SetStringField(TEXT("mode"), Mode);
	R->SetNumberField(TEXT("pre"), Pre);
	R->SetNumberField(TEXT("post"), Post);
	R->SetNumberField(TEXT("hz"), Hz);
	R->SetStringField(TEXT("lws_version"), AarsFdProbe::LwsVersion());
	R->SetNumberField(TEXT("tcp_nodelay"), NoDelay);
	R->SetNumberField(TEXT("connects"), Connects);
	R->SetNumberField(TEXT("disconnects"), Disconnects);
	R->SetNumberField(TEXT("concurrent_connects"), ConcurrentConnects);
	R->SetNumberField(TEXT("frames"), Frames);
	R->SetNumberField(TEXT("world_state_queued"), StateSent);
	R->SetNumberField(TEXT("burst_pairs"), BurstPairs);
	R->SetNumberField(TEXT("rx_msgs"), RxMsgs);
	R->SetNumberField(TEXT("rx_bytes"), RxBytes);
	R->SetNumberField(TEXT("rx_unparsed"), RxBad);
	R->SetNumberField(TEXT("pongs_queued"), PongsQueued);
	R->SetNumberField(TEXT("pod_hose_rx"), PodHose);
	R->SetNumberField(TEXT("pod_hose_seq_gaps"), PodHoseGaps);
	R->SetNumberField(TEXT("final_queue_depth"), FinalQueue);
	TSharedRef<FJsonObject> Types = MakeShared<FJsonObject>();
	for (const TPair<FString, int32>& P : RxTypes) Types->SetNumberField(P.Key, P.Value);
	R->SetObjectField(TEXT("rx_types"), Types);
	R->SetArrayField(TEXT("rx_samples"), RxSamples);
	R->SetObjectField(TEXT("tick_ms"), TickMs.ToJson());
	R->SetObjectField(TEXT("frame_period_ms"), FramePeriodMs.ToJson());
	R->SetObjectField(TEXT("frame_work_ms"), FrameWorkMs.ToJson());
	R->SetObjectField(TEXT("queue_depth"), QueueDepth.ToJson());

	FString Out;
	TSharedRef<TJsonWriter<>> W = TJsonWriterFactory<>::Create(&Out);
	FJsonSerializer::Serialize(R, W);
	if (!OutPath.IsEmpty()) FFileHelper::SaveStringToFile(Out, *OutPath, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
	UE_LOG(LogAarsWs, Display, TEXT("%s"), *Out);

	Server.Reset();
	return 0;
}
