import unreal
unreal.log("[GS3] %s" % [f for f in dir(unreal.GeometryScript_MeshQueries) if "triangle" in f or "valid" in f])
