"""Actual persisted FCStd/STEP validation, isolated from the checking process.

Floating-point comparisons below concern CAD serialization only, not real
manufacturing tolerances or permitted physical clearances.
"""
import argparse,json,math,subprocess,sys,tempfile,zipfile
from pathlib import Path
from layout_common import ROOT,load,selected,bounds,value,digest


class CadValidationError(ValueError):
    def __init__(self, code, message, **evidence):
        super().__init__(message)
        self.report={'status':'FAILED','code':code,'reason':message,**evidence}


def fail(message):raise ValueError(message)


def check_cad_adapter(data, models, input_path):
    models=Path(models).resolve();input_path=Path(input_path).resolve()
    try:
        if data!=load(input_path):fail('in-memory inputs differ from persisted inputs')
        for variant in 'AB':
            folder=models/variant;manifest=json.loads((folder/'manifest.json').read_text())
            if manifest['input_sha256']!=digest(input_path):fail('stale CAD input hash '+variant)
            records=manifest['objects'];names=[r['id'] for r in records]
            if len(names)!=len(set(names)) or set(names)!={c['id'] for c in selected(data,variant)}:fail('manifest object mismatch '+variant)
            for suffix in ('.FCStd','.step'):
                name='layout_'+variant+suffix;path=folder/name
                if not path.is_file() or not path.stat().st_size:fail('actual CAD missing/empty: '+str(path))
                expected=manifest['exports'].get(name)
                if not expected or digest(path)!=expected:fail('actual CAD hash mismatch: '+str(path))
        with tempfile.TemporaryDirectory(prefix='rev-cad-validation-') as tmp:
            output=Path(tmp)/'native.json'
            command=['/usr/bin/python3',str(Path(__file__).resolve()),'--inputs',str(input_path),'--models',str(models),'--out',str(output)]
            run=subprocess.run(command,text=True,capture_output=True,timeout=120)
            if run.returncode or not output.is_file():
                raise CadValidationError('NATIVE_VALIDATION_FAILED','native CAD validation did not complete successfully',exit_code=run.returncode,stdout=run.stdout,stderr=run.stderr,native=json.loads(output.read_text()) if output.is_file() else None)
            payload=json.loads(output.read_text())
            if payload.get('status')!='PASS':raise CadValidationError('NATIVE_VALIDATION_FAILED','native CAD reported failure',native=payload)
            return payload['variants']
    except CadValidationError:raise
    except (OSError,KeyError,TypeError,ValueError,subprocess.TimeoutExpired) as exc:
        raise CadValidationError('CAD_INPUT_INVALID',str(exc)) from exc


def close_number(a,b,volume=False):
    return math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-5 if volume else 1e-9)


def shape_bounds(shape):
    b=shape.optimalBoundingBox(False,False)
    return [b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax]


def same_shape(actual, expected):
    if actual.isNull() or not actual.isValid() or len(actual.Solids)!=1:return False
    if not all(close_number(a,b) for a,b in zip(shape_bounds(actual),shape_bounds(expected))):return False
    if not close_number(actual.Volume,expected.Volume,True):return False
    # A matching bound/volume signature alone is not shape correspondence.
    common=actual.common(expected)
    return close_number(common.Volume,actual.Volume,True) and close_number(common.Volume,expected.Volume,True)


def native_validate(input_path,models):
    sys.path.append('/usr/lib/freecad-python3/lib')
    import FreeCAD as App
    import Part
    data=load(input_path);results={}
    for variant in 'AB':
        folder=Path(models)/variant;path=folder/f'layout_{variant}.FCStd';step_path=folder/f'layout_{variant}.step'
        manifest=json.loads((folder/'manifest.json').read_text());records={r['id']:r for r in manifest['objects']}
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None or 'Document.xml' not in archive.namelist():fail('invalid FCStd archive')
        doc=None
        try:
            doc=App.openDocument(str(path));doc.recompute()
            objects={o.Name:o for o in doc.Objects if hasattr(o,'ResearchStatus')}
            expected_ids={c['id'] for c in selected(data,variant)}
            if set(objects)!=expected_ids:fail('FCStd body registry differs from inputs '+variant)
            if {o.Name for o in doc.Assembly.Group}!=expected_ids:fail('FCStd Assembly registry differs '+variant)
            queries={o.Name for o in doc.QueryVolumes.Group}
            if queries!=set(manifest['query_volumes']):fail('FCStd query registry mismatch '+variant)
            if any(getattr(o,'Role',None)!='QUERY_NOT_SOLID' for o in doc.QueryVolumes.Group):fail('invalid query volume role')
            solids={o.Name for o in doc.Objects if hasattr(o,'Shape') and not o.Shape.isNull() and o.Name not in queries and o.TypeId!='App::Part' and o.Shape.Solids}
            if solids!=expected_ids:fail('unexpected/missing unclassified FCStd solids '+variant)
            step=Part.read(str(step_path))
            if step.isNull() or not step.isValid() or len(step.Solids)!=len(expected_ids):fail('invalid STEP/count '+variant)
            unmatched=list(step.Solids);evidence=[]
            for c in selected(data,variant):
                name=c['id'];obj=objects[name]
                if obj.ResearchStatus!='ASSUMED_NOT_REV':fail('FCStd research status changed '+name)
                position=App.Vector(*[float(value(data,k))*1000 for k in c['position']])
                if c['kind']=='box':expected=Part.makeBox(*[float(value(data,k))*1000 for k in c['size']],position)
                else:expected=Part.makeCylinder(float(value(data,c['radius']))*1000,float(value(data,c['length']))*1000,position,App.Vector(1,0,0))
                if not same_shape(obj.Shape,expected):fail('actual FCStd geometry mismatch '+name)
                lo,hi=bounds(data,c);nominal=[float(x)*1000 for x in lo+hi];native=shape_bounds(obj.Shape)
                if not all(close_number(a,b) for a,b in zip(nominal,native)):fail('actual FCStd nominal bounds mismatch '+name)
                record=records[name]
                if record['kind']!=c['kind'] or len(record['cad_bounds_mm'])!=6 or not all(close_number(a,b) for a,b in zip(native,record['cad_bounds_mm'])):fail('manifest/native bounds mismatch '+name)
                if not close_number(record['volume_m3']*1e9,obj.Shape.Volume,True):fail('manifest/native volume mismatch '+name)
                # Unordered STEP solids must correspond one-to-one, including form.
                match=next((i for i,shape in enumerate(unmatched) if same_shape(shape,expected)),None)
                if match is None:fail('actual STEP geometry mismatch '+name)
                unmatched.pop(match)
                evidence.append({'id':name,'native_bounds_mm':native,'native_volume_mm3':obj.Shape.Volume,'FCStd_shape_match':'PASS','STEP_shape_match':'PASS'})
            for file in (path,step_path):
                if digest(file)!=manifest['exports'][file.name]:fail('artifact changed during validation '+file.name)
            results[variant]={'status':'PASS','nominal_bounds_match':'PASS','solid_count':len(objects),'actual_FCStd_reopen_recompute':'PASS','actual_STEP_shape_correspondence':'PASS','files':{file.name:digest(file) for file in (path,step_path)},'objects':evidence,'scope':'persisted ASSUMED native primitives/STEP checked; AABB movement scope unchanged; numerical serialization comparison, no manufacturing tolerance','FreeCAD_version':App.Version()[:3]}
        finally:
            if doc is not None:App.closeDocument(doc.Name)
    return results


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--inputs',required=True);parser.add_argument('--models',required=True);parser.add_argument('--out',required=True);args=parser.parse_args()
    try:
        result={'status':'PASS','variants':native_validate(args.inputs,args.models)};code=0
    except Exception as exc:
        result={'status':'FAILED','reason':str(exc),'exception':type(exc).__name__};code=1
    Path(args.out).write_text(json.dumps(result,indent=2)+'\n');return code


if __name__=='__main__':sys.exit(main())
