import unreal
w = unreal.EditorLevelLibrary.get_game_world()
unreal.SystemLibrary.execute_console_command(w, "HighResShot 1")
