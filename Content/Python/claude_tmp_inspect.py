import unreal, json
out=[]
bp=unreal.load_asset('/Game/AirRefueler/Models/Aircraft/KC135/BP_KC135')
sds=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
L=unreal.SubobjectDataBlueprintFunctionLibrary
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    data=L.get_data(h); obj=L.get_object(data)
    if obj is None: continue
    row={'name':str(L.get_variable_name(data)),'class':obj.get_class().get_name()}
    if isinstance(obj, unreal.SceneComponent):
        row['loc']=str(obj.get_editor_property('relative_location')); row['rot']=str(obj.get_editor_property('relative_rotation')); row['scale']=str(obj.get_editor_property('relative_scale3d'))
        p=obj.get_attach_parent(); row['parent']=p.get_name() if p else None
    if isinstance(obj, unreal.StaticMeshComponent):
        m=obj.get_editor_property('static_mesh'); row['mesh']=m.get_name() if m else None
    out.append(row)
sm=unreal.load_asset('/Game/AirRefueler/Models/Aircraft/KC135/Meshes/SM_KC135_6')
out.append({'bounds':str(sm.get_bounding_box())})
w=unreal.EditorLevelLibrary.get_editor_world()
out.append({'world':w.get_path_name() if w else None})
acts=[a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor) if 'KC135' in a.get_class().get_name() or 'KC' in a.get_actor_label()]
out.append({'kc_actors':[(a.get_actor_label(), str(a.get_actor_transform())) for a in acts]})
open(r'D:/GitHub/AirRefueler/Saved/claude_out.json','w').write(json.dumps(out,indent=1))
