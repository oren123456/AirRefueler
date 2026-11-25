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
BUILD_BAT = os.path.join(ENGINE, "Build", "BatchFiles", "Build.bat")
EDITOR_CMD = os.path.join(ENGINE, "Binaries", "Win64", "UnrealEditor-Cmd.exe")
RES = os.path.join(PROJ_DIR, "Results")
os.makedirs(RES, exist_ok=True)
sys.path.insert(0, HERE)
import ws_client  # noqa: E402

PORT = 8765
STATUS = os.path.join(RES, "status.txt")


def status(msg):
    with open(STATUS, "a") as f:
        f.write("%s %s\n" % (time.strftime("%H:%M:%S"), msg))


def build():
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
    cmd = [EDITOR_CMD, UPROJECT, "-run=AarsWsTest", "-port=%d" % PORT, "-out=" + out, "-ready=" + ready,
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
}


def main():
    args = sys.argv[1:]
    if os.path.exists(STATUS):
        os.remove(STATUS)
    status("engine " + ENGINE)
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
            time.sleep(0.5)
            cres = client()
            sres = finish_server(p, out)
            summary[name] = {"client": cres, "server": sres}
            status("%s done" % name)
        except Exception:
            summary[name] = {"error": traceback.format_exc()}
            status("%s ERROR" % name)
        with open(os.path.join(RES, "summary.json"), "w") as f:
            json.dump(summary, f, indent=1)
    status("DONE")


if __name__ == "__main__":
    main()
