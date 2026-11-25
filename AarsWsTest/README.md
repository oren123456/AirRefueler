# AarsWsTest — AARS link test project

Separate .uproject (not the AirRefueler game) for the World side of the **AARS ↔ World contract 0.2**:
Unreal's built-in **WebSocketNetworking** plugin (UE 5.8, libwebsockets 3.0.0) plus the contract messages.

**`Plugins/AarsLink`** — the part meant to move into AirRefueler (copy the folder into `AirRefueler/Plugins`):
- `AarsTypes.h` — every contract message as a Blueprint-visible `USTRUCT` / `UENUM` (units kept in the names: `TipFt`, `IasKt`, …).
- `AarsCodec.*` — World → Simulator writers (`hello`, `world.state`, `pong`, `snapshot.reply`) and a strict
  Simulator → World parser (unknown/missing fields, wrong types, bad enums and out-of-range values are rejected with the reason).
  `world.state` values outside the contract are made legal and reported (heading wrapped, angles clamped, NaN → 0, ids cut to 32, …).
- `AarsLinkServer.*` — WebSocket server: `Receive()` / `Send…()` / `Flush()` per frame, one `On…` event per Simulator message,
  `hello` on connect, automatic `pong`, version check, stale-`seq` drop for `pod.hose`/`boom.drive`, newest connection wins,
  refuses to start if another program already listens on the port (the plugin would otherwise share it silently).

**Test code**
- `Source/AarsWsTest/AarsFakeWorldCommandlet.*` — `-run=AarsFakeWorld`: a World with no 3D scene that speaks the whole contract
  (hose/boom follow the Simulator, demonstrator commands, clock, snapshot/replay). Usable as a stand-in World for the AARS team:
  `UnrealEditor-Cmd.exe AarsWsTest.uproject -run=AarsFakeWorld -port=8765 [-bind=0.0.0.0] [-restore]`
- `Source/AarsWsTest/AarsWsTestCommandlet.*` — `-run=AarsWsTest`: raw plugin measurements (Tick strategies, Nagle, framing).
- `Source/AarsWsTest/FdProbe.*` — test-only peek into the plugin's private `FWebSocket` (TCP_NODELAY, send-queue depth).
- `Tools/ws_console.html` — GUI client: open it in Chrome, connect to Unreal, send any contract message (templates from the
  contract examples, fresh `seq`/`t_ms`/ping id, optional repeat), see the latest `world.state`, a log, rates and ping RTT.
- `Tools/ws_client.py` — raw-socket WebSocket client (stdlib only) that records frames exactly as received.
- `Tools/contract_test.py` — plays the Simulator: all valid examples, checks the World's reaction, 14 contract-breaking messages,
  version mismatch, and validates every World message against `messages.schema.json`.
- `Tools/mini_schema.py` — stdlib JSON-Schema validator for the keywords the contract uses (agrees with `jsonschema` on 3,726
  mutated messages; stricter on one point: `1.0` is not an integer).
- `Tools/run_tests.py` — builds and runs everything. Results go to `Results/` (git-ignored).

The contract is read from `AirRefueler\AARS-world-contract-0.2\AARS-world-contract-0.2` (or `--contract <dir>`).
Tests use a free port picked at start (`--port <n>` to force one).

Run (Unreal's Python):
```
"<Engine>\Binaries\ThirdParty\Python3\Win64\python.exe" Tools\run_tests.py --build
```
The engine is taken from the python.exe path (or `--engine <dir>` / `UE_ENGINE`).
`--build` uses `-NoHotReloadFromIDE` so it builds while another editor of the same engine has Live Coding active.

## Contract results (2026-11-25, desktop-gc0ahoc)

- `contract`: **28/28** — hello first, ping/pong, clock scale + pause, pod.hose (incl. attached, cut, stale seq dropped),
  pod/boom fluid, camera.lens, boom.drive (incl. coupled: tip follows the hole), tanker.set (+ turn while banked),
  receiver add/command/remove (pod and boom), snapshot → world.set replay → world.resume, 14 bad messages rejected
  with nothing changed, version 0.3 ignored until a 0.2 hello, newest connection wins, every World message
  (hello, world.state ×179, pong, snapshot.reply) valid against the schema, restore in every 2nd world.state.
- `contract_fixes`: **5/5** — out-of-contract values in `FAarsWorldState` still produce schema-valid `world.state`.
- `port_busy`: **1/1** — port already taken → the World exits with an error instead of sharing it.

## Plugin results (2026-11-24, vrlab3, loopback; same on desktop-gc0ahoc 2026-11-25)

| Scenario | Server Tick() per frame | world.state arrivals (mean / p99 / max ms) | ping→pong RTT (mean / p99 / max ms) | send queue at end |
|---|---|---|---|---|
| naive_1tick | 1 | 19.4 / 33.4 / 33.5 (backlogged behind pongs) | 1131 / 2215 / 2231, growing | 151 msgs |
| tick_2 | 1 before + 1 after Send | 16.7 / 33.3 / 33.5 (a state slips one frame when a pong is ahead of it) | 15.3 / 16.0 / 16.1 | 0 |
| tick_4 | 1 before + 3 after Send | 16.7 / 17.0 / 17.2 | 15.5 / 16.1 / 16.1 | 0 |

- **TCP_NODELAY = 1** on the accepted socket (getsockopt). Back-to-back A/B messages with a silent client: gap 0.02 ms (no Nagle delay).
- **Outbound frames are always binary** (opcode 2). With `Send(..., false)` the payload is the raw JSON (starts with `{`).
- **One message per Tick()**: with 1 Tick per frame, world.state (60/s) + pong (10/s) exceed the drain rate → queue and latency grow without bound.
- **RTT** is bounded by how often Tick() runs: messages are read only inside Tick(). With 1 + 3 Ticks per frame: mean 15 ms / max 16 ms on vrlab3 (client and server clocks phase-locked), mean 9 ms / max 26 ms on desktop-gc0ahoc — inside the contract budget (mean ≤ 30, p99 ≤ 50).
- `Tick()` cost: mean 0.03–0.12 ms, max 0.65 ms; `lws_service(ctx, 0)` does not block. Frame period 16.67 ms (p99 16.8).
- Inbound **text** frames: OK, including fragmented messages and a 200 KB message (echoed back intact).
- Inbound **binary** frames: silently lost (raw JSON) — the plugin reads them as `[uint32 size][payload]`. A bad binary frame also poisons that connection's binary buffer.
- Subprotocol: none → accepted; `binary` → accepted; any other (e.g. `aars`) → connection closed during handshake.
- A second concurrent client is accepted (the server cannot refuse it except via the Origin/IP filter callback, and cannot close a connection).
- Reconnect after close: works (pong + world.state on the new connection).
- No pod.hose loss or reordering (900/900, 0 seq gaps).
