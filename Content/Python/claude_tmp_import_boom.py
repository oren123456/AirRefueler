import unreal, json
out={}
dst='/Game/AirRefueler/Models/Aircraft/KC135/Meshes/Boom'
base='D:/GitHub/AirRefueler/Data/Generated/KC135/Boom/'
mi=unreal.load_asset('/Game/AirRefueler/Models/Aircraft/KC135/Materials/MI_KC135_Detail')
tasks=[]
for n in ['Boom_Outer','Boom_Telescope','Ruddevator_L','Ruddevator_R']:
    t=unreal.AssetImportTask(); t.filename=base+'SM_KC135_'+n+'.obj'; t.destination_path=dst; t.destination_name='SM_KC135_'+n
    t.automated=True; t.replace_existing=True; t.save=False; tasks.append(t)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
for t in tasks:
    out[t.destination_name]={'imported':[str(p) for p in t.imported_object_paths]}
for n in ['Boom_Outer','Boom_Telescope','Ruddevator_L','Ruddevator_R']:
    p=dst+'/SM_KC135_'+n
    sm=unreal.load_asset(p)
    if not sm: out[n]='missing'; continue
    mats=sm.get_editor_property('static_materials')
    for i in range(len(mats)): sm.set_material(i, mi)
    bb=sm.get_bounding_box()
    out[n]={'min':[bb.min.x,bb.min.y,bb.min.z],'max':[bb.max.x,bb.max.y,bb.max.z],'slots':len(mats),'tris':sm.get_num_triangles(0)}
open(r'D:/GitHub/AirRefueler/Saved/claude_out.json','w').write(json.dumps(out,indent=1))
