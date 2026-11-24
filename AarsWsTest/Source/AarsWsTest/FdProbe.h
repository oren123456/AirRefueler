#pragma once
#include "CoreMinimal.h"

class INetworkingWebSocket;

// Test-only access to FWebSocket internals. Returns false when the probe is compiled out.
namespace AarsFdProbe
{
	// TCP_NODELAY of the connection's real socket: 1 = Nagle off, 0 = Nagle on, -1 = error.
	bool GetNoDelay(INetworkingWebSocket* Socket, int32& OutNoDelay);
	// Messages waiting in FWebSocket::OutgoingBuffer.
	bool GetQueueDepth(INetworkingWebSocket* Socket, int32& OutDepth);
	FString LwsVersion();
}
