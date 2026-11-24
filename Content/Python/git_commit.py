"""git add (argv paths, default -A) + commit with the message in Saved/ClaudeShots/commit_msg.txt (Windows git). Output -> Saved/ClaudeShots/git_out.txt"""
import subprocess, unreal, sys
root = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
out = []
add = ["add", "-A"] if len(sys.argv) < 2 else ["add", "-A", "--"] + sys.argv[1:]
for args in (add, ["commit", "-F", root + "Saved/ClaudeShots/commit_msg.txt"], ["log", "--oneline", "-3"]):
    r = subprocess.run(["git"] + args, cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out.append("$ git %s\nRC=%d\n%s\n%s" % (" ".join(args), r.returncode, r.stdout, r.stderr))
open(root + "Saved/ClaudeShots/git_out.txt", "w", encoding="utf-8").write("\n".join(out))
unreal.log("[GitCommit] done")
