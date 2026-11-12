"""Record corrected R5 counterexamples and actual-CAD negative evidence."""
import argparse,copy,json,shutil,subprocess,sys,tempfile
from pathlib import Path
from layout_common import ROOT,load,digest,config
from cad_validation import check_cad_adapter,CadValidationError
from test_lifecycle import observations


def native_mutate(models, mode, shift):
    sys.path.append('/usr/lib/freecad-python3/lib')
    import FreeCAD as App
    import Part
    p=Path(models)/'A'
    if mode=='edited_fcstd':
        d=App.openDocument(str(p/'layout_A.FCStd'))
        try:
            original=d.Inputs.get('B1').Value;d.Inputs.set('B1','='+str(original+shift)+' mm');d.recompute();d.save()
        finally:App.closeDocument(d.Name)
    else:
        shapes=list(Part.read(str(p/'layout_A.step')).Solids);shapes[0].translate(App.Vector(shift,0,0))
        d=App.newDocument('RegressionSTEP')
        try:
            objects=[]
            for i,shape in enumerate(shapes):
                obj=d.addObject('Part::Feature','Mutated'+str(i));obj.Shape=shape;objects.append(obj)
            d.recompute();Part.export(objects,str(p/'layout_A.step'))
        finally:App.closeDocument(d.Name)


def cad_observations(models,input_path):
    data=load(input_path);output=[]
    cases=('manifest_only','missing_fcstd','missing_step','empty_fcstd','corrupt_fcstd_old_hash','corrupt_step_old_hash','corrupt_fcstd_new_hash','corrupt_step_new_hash','edited_fcstd','edited_step','altered_manifest_bounds','missing_export_hash','duplicate_manifest_body','missing_manifest')
    for case in cases:
        with tempfile.TemporaryDirectory(prefix='rev-cad-negative-') as tmp:
            root=Path(tmp)
            for v in 'AB':
                folder=root/v;folder.mkdir()
                for name in ('manifest.json',f'layout_{v}.FCStd',f'layout_{v}.step'):shutil.copyfile(Path(models)/v/name,folder/name)
            a=root/'A';manifest=json.loads((a/'manifest.json').read_text())
            if case=='manifest_only':
                for p in root.glob('*/layout_*'):p.unlink()
            elif case=='missing_fcstd':(a/'layout_A.FCStd').unlink()
            elif case=='missing_step':(root/'B/layout_B.step').unlink()
            elif case=='empty_fcstd':(a/'layout_A.FCStd').write_bytes(b'')
            elif case.startswith('corrupt_'):
                path=a/('layout_A.FCStd' if 'fcstd' in case else 'layout_A.step');path.write_bytes(b'not a CAD document')
                if case.endswith('new_hash'):manifest['exports'][path.name]=digest(path)
            elif case in ('edited_fcstd','edited_step'):
                native_mutate(root,case,float(config(data,'obstacle_thickness'))*1000)
                name='layout_A.FCStd' if case=='edited_fcstd' else 'layout_A.step';manifest['exports'][name]=digest(a/name)
            elif case=='altered_manifest_bounds':manifest['objects'][0]['cad_bounds_mm'][0]+=float(config(data,'obstacle_thickness'))*1000
            elif case=='missing_export_hash':del manifest['exports']['layout_A.FCStd']
            elif case=='duplicate_manifest_body':manifest['objects'].append(copy.deepcopy(manifest['objects'][0]))
            (a/'manifest.json').write_text(json.dumps(manifest))
            if case=='missing_manifest':(a/'manifest.json').unlink()
            try:
                result=check_cad_adapter(data,root,input_path);row={'id':case,'observed_status':'PASS','native':result,'matches':False}
            except CadValidationError as exc:
                row={'id':case,'observed_status':'FAILED','evidence':exc.report,'matches':True}
            output.append(row)
    return output


def main():
    p=argparse.ArgumentParser();p.add_argument('--models',required=True);p.add_argument('--inputs',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    lifecycle=observations();cad=cad_observations(a.models,a.inputs)
    okay=all(r['matches'] for r in lifecycle+cad)
    sources=[Path(__file__),Path(__file__).with_name('test_lifecycle.py'),Path(__file__).with_name('layout_lifecycle.py'),Path(__file__).with_name('cad_validation.py')]
    result={'status':'PASS' if okay else 'FAIL','scope':'tool regressions only; no geometric correction','R5_input':'e939b41d0139b0a3a08a5950eeeec6e92324cf9b','source_hashes':{str(f.relative_to(ROOT)):digest(f) for f in sources},'lifecycle':lifecycle,'CAD':cad}
    Path(a.out).write_text(json.dumps(result,indent=2)+'\n');print(f'{len(lifecycle)} lifecycle cases, {len(cad)} CAD negative cases: '+result['status']);return 0 if okay else 1


if __name__=='__main__':sys.exit(main())
