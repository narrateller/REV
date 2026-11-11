"""Negative native-query regressions; mutated copies never change layout inputs."""
import argparse,json,shutil,subprocess,sys,tempfile
from pathlib import Path
from layout_common import ROOT,load,config,digest
from query_volumes import QUERY_SOURCES
from cad_validation import check_cad_adapter,CadValidationError

MODES=('size_length','size_width','size_height','move_x','move_y','move_z','delete','delete_forged_manifest','substitute_form','empty','shape_override','wrong_role','size_and_position','stale_hash')


def mutate(folder,variant,name,mode,shift):
    sys.path.append('/usr/lib/freecad-python3/lib')
    import FreeCAD as App
    import Part
    path=folder/variant/f'layout_{variant}.FCStd';doc=App.openDocument(str(path));before={};after={}
    try:
        zone=doc.getObject(name);before={'dimensions_mm':[zone.Length.Value,zone.Width.Value,zone.Height.Value],'position_mm':list(zone.Placement.Base)}
        if mode.startswith('size_') and mode!='size_and_position' or mode=='stale_hash':
            prop={'size_length':'Length','size_width':'Width','size_height':'Height','stale_hash':'Height'}[mode]
            zone.setExpression(prop,None);setattr(zone,prop,99999 if name=='CylinderRemoval' and mode=='size_height' else getattr(zone,prop).Value+shift)
        elif mode.startswith('move_') or mode=='size_and_position':
            axis='xyz'.index(mode[-1]) if mode.startswith('move_') else 0
            zone.setExpression('Placement.Base.'+'xyz'[axis],None);place=zone.Placement;vector=list(place.Base);vector[axis]+=shift;place.Base=App.Vector(*vector);zone.Placement=place
            if mode=='size_and_position':zone.setExpression('Height',None);zone.Height=zone.Height.Value+shift
        elif mode in ('delete','delete_forged_manifest'):doc.removeObject(name)
        elif mode in ('substitute_form','empty'):
            pos=zone.Placement.Base;length,width,height=before['dimensions_mm'];doc.removeObject(name)
            obj=doc.addObject('Part::Feature',name);doc.QueryVolumes.addObject(obj);obj.addProperty('App::PropertyString','Role');obj.Role='QUERY_NOT_SOLID'
            obj.Shape=Part.Shape() if mode=='empty' else Part.makeCylinder(width/2,height,pos)
        elif mode=='wrong_role':zone.Role='SOLID'
        elif mode=='group_move':place=doc.QueryVolumes.Placement;place.Base=App.Vector(shift,0,0);doc.QueryVolumes.Placement=place
        elif mode=='group_missing':doc.removeObject('QueryVolumes')
        elif mode=='extra_query_forged_manifest' or mode=='orphan_empty_query':
            extra=doc.addObject('Part::Feature','UnspecifiedQuery');extra.addProperty('App::PropertyString','Role');extra.Role='QUERY_NOT_SOLID'
            extra.Shape=Part.Shape() if mode=='orphan_empty_query' else zone.Shape.copy()
            if mode=='extra_query_forged_manifest':doc.QueryVolumes.addObject(extra)
        doc.recompute()
        if mode=='shape_override':
            zone.Shape=Part.makeCylinder(before['dimensions_mm'][1]/2,before['dimensions_mm'][2],zone.Placement.Base)
        target=doc.getObject(name)
        after={'exists':target is not None,'null_shape':target.Shape.isNull() if target is not None else None,'type':target.TypeId if target is not None else None}
        doc.save()
    finally:App.closeDocument(doc.Name)
    manifest_path=folder/variant/'manifest.json';manifest=json.loads(manifest_path.read_text())
    if mode!='stale_hash':manifest['exports'][path.name]=digest(path)
    if mode=='delete_forged_manifest':manifest['query_volumes'].remove(name)
    if mode=='extra_query_forged_manifest':manifest['query_volumes'].append('UnspecifiedQuery')
    manifest_path.write_text(json.dumps(manifest)+'\n')
    return {'before':before,'after':after,'hash_updated':mode!='stale_hash'}


def run_case(models,input_path,variant,name,mode,check_cli=False):
    data=load(input_path)
    with tempfile.TemporaryDirectory(prefix='rev-query-negative-') as tmp:
        root=Path(tmp)
        for v in 'AB':
            (root/v).mkdir()
            for file in ('manifest.json',f'layout_{v}.FCStd',f'layout_{v}.step'):shutil.copyfile(Path(models)/v/file,root/v/file)
        mutation=mutate(root,variant,name,mode,float(config(data,'service_lift'))*1000)
        row={'id':variant+'/'+name+'/'+mode,'expected':'FAILED','mutation':mutation}
        try:r=check_cad_adapter(data,root,input_path);row.update(observed='PASS',matches=False)
        except CadValidationError as exc:
            native=exc.report.get('native') or {};reason=native.get('reason','')
            appropriate=exc.report['code']=='CAD_INPUT_INVALID' if mode=='stale_hash' else exc.report['code']=='NATIVE_VALIDATION_FAILED' and any(w in reason.lower() for w in ('query','queries','canonical'))
            row.update(observed='FAILED',matches=appropriate,evidence=exc.report)
        if check_cli:
            out=root/'checks';out.mkdir();(out/'report.json').write_text('{"status":"PASS"}')
            command=['/usr/bin/python3',str(ROOT/'cad/layout/check_layout.py'),'--inputs',str(input_path),'--models',str(root),'--out',str(out)]
            run=subprocess.run(command,text=True,capture_output=True);result=json.loads((out/'report.json').read_text())
            row['CLI']={'exit_code':run.returncode,'status':result['status'],'scenarios':result.get('scenarios'),'cad_adapter':result.get('cad_adapter')}
            row['matches']=row['matches'] and run.returncode!=0 and result['status']=='FAILED' and result['scenarios']=='NOT_RUN'
        return row


def main():
    p=argparse.ArgumentParser();p.add_argument('--models',required=True);p.add_argument('--inputs',required=True);p.add_argument('--out',required=True);a=p.parse_args();rows=[]
    for variant in 'AB':
        for name in QUERY_SOURCES:
            for mode in MODES:rows.append(run_case(a.models,a.inputs,variant,name,mode,variant=='A' and name=='CylinderRemoval' and mode=='size_height'))
        for mode in ('group_move','group_missing','extra_query_forged_manifest','orphan_empty_query'):
            rows.append(run_case(a.models,a.inputs,variant,'CylinderRemoval',mode))
    okay=all(r['matches'] for r in rows)
    sources=[Path(__file__),Path(__file__).with_name('query_volumes.py'),Path(__file__).with_name('cad_validation.py')]
    report={'status':'PASS' if okay else 'FAIL','R5_input':'8f381c4b080d902cb023429c54d518bfd6fab681','scope':'native QueryVolumes correspondence only; geometry and B01 unchanged','source_hashes':{str(p.relative_to(ROOT)):digest(p) for p in sources},'case_count':len(rows),'cases':rows}
    Path(a.out).write_text(json.dumps(report,indent=2)+'\n');print(str(len(rows))+' QueryVolumes negative cases: '+report['status']);return 0 if okay else 1


if __name__=='__main__':sys.exit(main())
