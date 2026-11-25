"""Export textures to Saved/ClaudeShots/export/<name>.png. Usage: py export_tex.py /Game/path/T_x ..."""
import unreal, sys, os
d = os.path.join(unreal.Paths.project_saved_dir(), "ClaudeShots", "export"); os.makedirs(d, exist_ok=True)
for p in sys.argv[1:]:
    t = unreal.load_asset(p)   # works during PIE too
    task = unreal.AssetExportTask(); task.object = t; task.filename = os.path.join(d, t.get_name() + ".png")
    task.automated = True; task.replace_identical = True; task.prompt = False
    task.exporter = unreal.TextureExporterPNG()
    ok = unreal.Exporter.run_asset_export_task(task)
    unreal.log("[Export] %s -> %s %s (%dx%d)" % (p, task.filename, ok, t.blueprint_get_size_x(), t.blueprint_get_size_y()))
