import unreal, sys
w = unreal.EditorLevelLibrary.get_game_world()
for c in sys.argv[1:]:
    unreal.SystemLibrary.execute_console_command(w, c)
unreal.log("[SimConsole] " + " | ".join(sys.argv[1:]))
