"""Builds AarsWsTest and runs the WebSocketNetworking scenarios. Run with Unreal's python.exe:
   <Engine>/Binaries/ThirdParty/Python3/Win64/python.exe run_tests.py [--build] [--only name,...] [--engine <dir>]"""
import json, os, subprocess, sys, time, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(HERE)
UPROJECT = os.path.join(PROJ_DIR, "AarsWsTest.uproject")
def find_engine():
    """Engine dir: --engine <dir>, UE_ENGINE env var, or the usual UE 5.8 install locations."""
    if "--engine" in sys.argv:
        return sys.argv[sys.argv.index("--engine") + 1]
    if os.environ.get("UE_ENGINE"):
        return os.environ["UE_ENGINE"]
    # the python.exe running this script is usually Unreal's own: <Engine>/Binaries/ThirdParty/Python3/Win64/python.exe
    exe = os.path.abspath(sys.executable)
    if os.sep.join(["Binaries", "ThirdParty", "Python3"]) in exe:
        return exe.split(os.sep + "Binaries" + os.sep)[0]
    for c in (r"C:\Program Files\Epic Games\UE_5.8\Engine", r"D:\Epic Games\UE_5.8\Engine", r"D:\Program Files\Epic Games\UE_5.8\Engine"):
        if os.path.isdir(c):
            return c
    raise SystemExit("Unreal Engine 5.8 not found: pass --engine <dir> or set UE_ENGINE")


ENGINE = find_engine()


def find_contract():
    """AARS contract folder (schema/ + examples/): --contract <dir>, or next to the AirRefueler project."""
    if "--contract" in sys.argv:
        return sys.argv[sys.argv.index("--contract") + 1]
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    repo = os.path.dirname(repo)  # AirRefueler
    for rel in (r"AARS-world-contract-0.2\AARS-world-contract-0.2", "AARS-world-contract-0.2", r"Data\AARS-world-contract-0.2"):
        d = os.path.join(repo, rel)
        if os.path.isfile(os.path.join(d, "schema", "messages.schema.json")):
            return d
    return None
BUILD_BAT = os.path.join(ENGINE, "Build", "BatchFiles", "Build.bat")
EDITOR_CMD = os.path.join(ENGINE, "Binaries", "Win64", "UnrealEditor-Cmd.exe")
RES = os.path.join(PROJ_DIR, "Results")
os.makedirs(RES, exist_ok=True)
sys.path.insert(0, HERE)
import ws_client  # noqa: E402
import contract_test  # noqa: E402

def free_port():
    """A port nothing listens on (8765 may be taken by another program on this PC). --port <n> to force one."""
    if "--port" in sys.argv:
        return int(sys.argv[sys.argv.index("--port") + 1])
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


PORT = free_port()
CONTRACT = find_contract()
STATUS = os.path.join(RES, "status.txt")


def status(msg):
    with open(STATUS, "a") as f:
        f.write("%s %s\n" % (time.strftime("%H:%M:%S"), msg))


def sync_plugin():
    """AarsLink lives in AirRefueler/Plugins. AarsWsTest builds its own copy (git-ignored) so the two projects never
    share or mix plugin DLLs (an external plugin dir made each project load two copies -> duplicate UClass crash)."""
    import filecmp, shutil
    src = os.path.join(os.path.dirname(PROJ_DIR), "Plugins", "AarsLink")
    dst = os.path.join(PROJ_DIR, "Plugins", "AarsLink")
    for sub in ("Source",):
        if os.path.isdir(os.path.join(dst, sub)):
            shutil.rmtree(os.path.join(dst, sub))
        shutil.copytree(os.path.join(src, sub), os.path.join(dst, sub))
    shutil.copy2(os.path.join(src, "AarsLink.uplugin"), os.path.join(dst, "AarsLink.uplugin"))
    status("plugin synced from " + src)


def build():
    sync_plugin()
    status("build start")
    with open(os.path.join(RES, "build.log"), "w") as log:
        rc = subprocess.call([BUILD_BAT, "AarsWsTestEditor", "Win64", "Development", "-Project=" + UPROJECT, "-WaitMutex", "-NoHotReloadFromIDE"],
                             stdout=log, stderr=subprocess.STDOUT)
    status("build rc=%d" % rc)
    return rc == 0


def start_server(name, args):
    ready = os.path.join(RES, name + ".ready")
    out = os.path.join(RES, name + ".server.json")
    for p in (ready, out):
        if os.path.exists(p):
            os.remove(p)
    run = [a for a in args if a.startswith("-run=")] or ["-run=AarsWsTest"]
    args = [a for a in args if not a.startswith("-run=")]
    cmd = [EDITOR_CMD, UPROJECT] + run + ["-port=%d" % PORT, "-out=" + out, "-ready=" + ready,
           "-nullrhi", "-unattended", "-nopause", "-nosplash", "-NoSound", "-NoShaderCompile",
           "-abslog=" + os.path.join(RES, name + ".server.log")] + args
    p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t0 = time.time()
    while not os.path.exists(ready):
        if p.poll() is not None:
            raise RuntimeError("server exited early rc=%s" % p.returncode)
        if time.time() - t0 > 300:
            p.kill()
            raise RuntimeError("server not ready after 300 s")
        time.sleep(0.25)
    status("%s server ready after %.1f s" % (name, time.time() - t0))
    return p, out


def finish_server(p, out, timeout=60):
    try:
        p.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
    try:
        return json.load(open(out, encoding="utf-8"))
    except Exception as e:
        return {"error": "no server json: %s" % e}


SCENARIOS = {
    # name: (server args, client function)
    "naive_1tick":  (["-mode=stream", "-pre=1", "-post=0", "-seconds=40"], lambda: ws_client.run_stream(PORT, 15)),
    "tick_2":       (["-mode=stream", "-pre=1", "-post=1", "-seconds=40"], lambda: ws_client.run_stream(PORT, 15)),
    "tick_4":       (["-mode=stream", "-pre=1", "-post=3", "-seconds=40"], lambda: ws_client.run_stream(PORT, 15)),
    "nagle_quiet":  (["-mode=nagle", "-pre=1", "-post=3", "-seconds=30"], lambda: ws_client.run_quiet_burst(PORT, 10)),
    "framing":      (["-mode=stream", "-pre=1", "-post=3", "-seconds=30"], lambda: ws_client.run_framing(PORT)),
    # contract 0.2 end to end against the fake World (AarsLink plugin)
    "contract":     (["-run=AarsFakeWorld", "-bind=127.0.0.1", "-restore", "-allowquit", "-seconds=90"], lambda: contract_test.run_contract(PORT, CONTRACT)),
    "contract_fixes": (["-run=AarsFakeWorld", "-bind=127.0.0.1", "-badvalues", "-allowquit", "-seconds=60"], lambda: contract_test.run_fixes(PORT, CONTRACT)),
}


def port_busy_test():
    """Another program listens on the port: the fake World must refuse to start (exit code 1), not share the port."""
    import socket
    blocker = socket.socket()
    blocker.bind(("127.0.0.1", PORT))
    blocker.listen(1)
    log = os.path.join(RES, "port_busy.server.log")
    try:
        p = subprocess.Popen([EDITOR_CMD, UPROJECT, "-run=AarsFakeWorld", "-port=%d" % PORT, "-bind=127.0.0.1", "-seconds=20",
                              "-nullrhi", "-unattended", "-nopause", "-nosplash", "-NoSound", "-abslog=" + log],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            rc = p.wait(timeout=120)
        except subprocess.TimeoutExpired:
            p.kill()
            rc = None
    finally:
        blocker.close()
    text = open(log, encoding="utf-8", errors="replace").read() if os.path.exists(log) else ""
    ok = rc not in (0, None) and "cannot use port" in text
    return {"checks": [{"check": "port already in use -> World refuses to start", "ok": ok, "detail": "" if ok else "rc=%s" % rc}],
            "passed": int(ok), "total": 1}


def main():
    args = sys.argv[1:]
    if os.path.exists(STATUS):
        os.remove(STATUS)
    status("engine " + ENGINE)
    status("contract " + str(CONTRACT))
    status("port %d" % PORT)
    if "--build" in args and not build():
        status("DONE (build failed)")
        return
    only = None
    if "--only" in args:
        only = args[args.index("--only") + 1].split(",")
    summary = {}
    for name, (sargs, client) in SCENARIOS.items():
        if only and name not in only:
            continue
        try:
            status("%s start" % name)
            p, out = start_server(name, sargs)
            try:
                time.sleep(0.5)
                cres = client()
            finally:
                sres = finish_server(p, out)
            summary[name] = {"client": cres, "server": sres}
            extra = " %d/%d checks passed" % (cres["passed"], cres["total"]) if isinstance(cres, dict) and "passed" in cres else ""
            status("%s done%s" % (name, extra))
        except Exception:
            summary[name] = {"error": traceback.format_exc()}
            status("%s ERROR" % name)
        with open(os.path.join(RES, "summary.json"), "w") as f:
            json.dump(summary, f, indent=1)
    if not only or "port_busy" in only:
        status("port_busy start")
        r = port_busy_test()
        summary["port_busy"] = {"client": r}
        status("port_busy done %d/%d checks passed" % (r["passed"], r["total"]))
        with open(os.path.join(RES, "summary.json"), "w") as f:
            json.dump(summary, f, indent=1)
    status("DONE")


if __name__ == "__main__":
    main()
