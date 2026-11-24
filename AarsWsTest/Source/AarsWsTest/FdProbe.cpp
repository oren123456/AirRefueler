#include "FdProbe.h"

#if WITH_FD_PROBE

#include "WebSocket.h" // private FWebSocket (test only)

#if PLATFORM_WINDOWS
#include "Windows/AllowWindowsPlatformTypes.h"
#include <winsock2.h>
#include <ws2tcpip.h>
#include "Windows/HideWindowsPlatformTypes.h"
#endif

#define UI UI_ST
THIRD_PARTY_INCLUDES_START
#include "libwebsockets.h"
THIRD_PARTY_INCLUDES_END
#undef UI

bool AarsFdProbe::GetNoDelay(INetworkingWebSocket* Socket, int32& OutNoDelay)
{
	OutNoDelay = -1;
	if (!Socket) return false;
	FWebSocket* Ws = static_cast<FWebSocket*>(Socket);
	lws_sockfd_type Fd = lws_get_socket_fd(Ws->Wsi);
	int Value = 0;
#if PLATFORM_WINDOWS
	int Len = sizeof(Value);
	if (getsockopt(Fd, IPPROTO_TCP, TCP_NODELAY, (char*)&Value, &Len) != 0) return true;
#else
	socklen_t Len = sizeof(Value);
	if (getsockopt(Fd, IPPROTO_TCP, TCP_NODELAY, &Value, &Len) != 0) return true;
#endif
	OutNoDelay = Value ? 1 : 0;
	return true;
}

bool AarsFdProbe::GetQueueDepth(INetworkingWebSocket* Socket, int32& OutDepth)
{
	OutDepth = -1;
	if (!Socket) return false;
	OutDepth = static_cast<FWebSocket*>(Socket)->OutgoingBuffer.Num();
	return true;
}

FString AarsFdProbe::LwsVersion()
{
	return FString(ANSI_TO_TCHAR(lws_get_library_version()));
}

#else

bool AarsFdProbe::GetNoDelay(INetworkingWebSocket*, int32& OutNoDelay) { OutNoDelay = -2; return false; }
bool AarsFdProbe::GetQueueDepth(INetworkingWebSocket*, int32& OutDepth) { OutDepth = -2; return false; }
FString AarsFdProbe::LwsVersion() { return TEXT("n/a"); }

#endif
