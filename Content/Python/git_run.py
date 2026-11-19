"""Run git in the project folder (Windows git) and write output to Saved/ClaudeShots/git_out.txt.
argv: git args...   e.g. ['x','status','--short']"""
import subprocess, sys, unreal
root = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
r = subprocess.run(["git"] + sys.argv[1:], cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace")
open(root + "Saved/ClaudeShots/git_out.txt", "w", encoding="utf-8").write("RC=%d\n%s\n---STDERR---\n%s" % (r.returncode, r.stdout, r.stderr))
unreal.log("[GitRun] rc=%d %s" % (r.returncode, " ".join(sys.argv[1:3])))
