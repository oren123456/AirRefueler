# AarsWsTest — WebSocketNetworking plugin test (throwaway)

Tests Unreal's built-in **WebSocketNetworking** plugin (UE 5.8, libwebsockets 3.0.0) as the World-side server for the
AARS ↔ World contract 0.2. Not part of the AirRefueler game; separate .uproject.

- `Source/AarsWsTest/AarsWsTestCommandlet.*` — server at 60 Hz (`-run=AarsWsTest`), sends `world.state`, answers `ping` with `pong`.
- `Source/AarsWsTest/FdProbe.*` — test-only peek into the plugin's private `FWebSocket` (TCP_NODELAY, send-queue depth).
- `Tools/ws_client.py` — raw-socket WebSocket client (stdlib only) that records frames exactly as received.
- `Tools/run_tests.py` — builds and runs all scenarios. Results go to `Results/` (git-ignored).

Run (Unreal's Python):
```
"D:\Epic Games\UE_5.8\Engine\Binaries\ThirdParty\Python3\Win64\python.exe" Tools\run_tests.py --build
```
`--build` uses `-NoHotReloadFromIDE` so it builds while another editor of the same engine has Live Coding active.

## Results (2026-11-24, vrlab3, loopback)

| Scenario | Server Tick() per frame | world.state arrivals (mean / p99 / max ms) | ping→pong RTT (mean / p99 / max ms) | send queue at end |
|---|---|---|---|---|
| naive_1tick | 1 | 19.4 / 33.4 / 33.5 (backlogged behind pongs) | 1131 / 2215 / 2231, growing | 151 msgs |
| tick_2 | 1 before + 1 after Send | 16.7 / 33.3 / 33.5 (a state slips one frame when a pong is ahead of it) | 15.3 / 16.0 / 16.1 | 0 |
| tick_4 | 1 before + 3 after Send | 16.7 / 17.0 / 17.2 | 15.5 / 16.1 / 16.1 | 0 |

- **TCP_NODELAY = 1** on the accepted socket (getsockopt). Back-to-back A/B messages with a silent client: gap 0.02 ms (no Nagle delay).
- **Outbound frames are always binary** (opcode 2). With `Send(..., false)` the payload is the raw JSON (starts with `{`).
- **One message per Tick()**: with 1 Tick per frame, world.state (60/s) + pong (10/s) exceed the drain rate → queue and latency grow without bound.
- **RTT** is bounded by how often Tick() runs: messages are read only inside Tick(), so a reply waits 0–16.7 ms at 60 Hz (here ~15 ms because client and server clocks were phase-locked).
- `Tick()` cost: mean 0.03–0.12 ms, max 0.65 ms; `lws_service(ctx, 0)` does not block. Frame period 16.67 ms (p99 16.8).
- Inbound **text** frames: OK, including fragmented messages and a 200 KB message (echoed back intact).
- Inbound **binary** frames: silently lost (raw JSON) — the plugin reads them as `[uint32 size][payload]`. A bad binary frame also poisons that connection's binary buffer.
- Subprotocol: none → accepted; `binary` → accepted; any other (e.g. `aars`) → connection closed during handshake.
- A second concurrent client is accepted (the server cannot refuse it except via the Origin/IP filter callback, and cannot close a connection).
- Reconnect after close: works (pong + world.state on the new connection).
- No pod.hose loss or reordering (900/900, 0 seq gaps).
