"""Counterexamples on copied native files, with updated hashes where appropriate."""
import json,sys,shutil,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'cad/calculated_layout'))
from native import App,Part,OUT,validate,save,digest,AUDIT

def main():
    results=[]
    cases=[(q,op) for q in ('CylinderRemoval','DoserRemoval') for op in ('size','position','delete','shape','empty')]
    cases += [('BoreMinimum','size'),('FCStd','missing'),('FCStd','corrupt'),('STEP','missing'),('STEP','corrupt'),('manifest','stale'),('Assembly','position'),('References','position'),('punch','detach_expression')]
    for name,op in cases:
        with tempfile.TemporaryDirectory(prefix='rev-cl-native-negative-') as temp:
            dest=Path(temp);shutil.copytree(OUT/'A',dest/'A');path=dest/'A/layout_A.FCStd';step=dest/'A/layout_A.step';manifest=json.loads((dest/'A/manifest.json').read_text())
            if name in ('CylinderRemoval','DoserRemoval','BoreMinimum','Assembly','References','punch'):
                doc=App.openDocument(str(path));obj=doc.getObject(name)
                if op=='size':
                    prop='Radius' if name=='BoreMinimum' else 'Length';obj.setExpression(prop,None);setattr(obj,prop,getattr(obj,prop).Value+1)
                elif op=='position':obj.setExpression('Placement.Base.x',None);obj.Placement.Base.x+=1
                elif op=='detach_expression':obj.setExpression('Width',None)
                elif op=='delete':doc.removeObject(name)
                elif op in ('shape','empty'):
                    doc.removeObject(name);obj=doc.addObject('Part::Feature',name);obj.addProperty('App::PropertyString','Role');obj.Role='QUERY_NOT_SOLID';doc.QueryVolumes.addObject(obj);obj.Shape=Part.makeSphere(1) if op=='shape' else Part.Shape()
                doc.recompute();doc.saveAs(str(path));App.closeDocument(doc.Name);manifest['exports'][path.name]=digest(path)
            elif name=='FCStd':
                path.unlink() if op=='missing' else path.write_bytes(b'corrupted FCStd fixture')
                if op!='missing':manifest['exports'][path.name]=digest(path)
            elif name=='STEP':
                step.unlink() if op=='missing' else step.write_bytes(b'not a valid STEP')
                if op!='missing':manifest['exports'][step.name]=digest(step)
            elif name=='manifest':manifest['input_sha256']='0'*64
            save(dest/'A/manifest.json',manifest)
            try:validate('A',dest);accepted=True;reason=None
            except Exception as exc:accepted=False;reason=str(exc)
            assert not accepted,(name,op)
            results.append({'object':name,'mutation':op,'rehash_edited_artifact':op!='missing','accepted':accepted,'reason':reason,'test_expectation_match':True})
    save(AUDIT/'native_regressions.json',{'test_result':'PASS','cases':results,'original_native_files':'UNCHANGED','scope':'all two QueryVolumes, reference bore and missing/corrupt/stale actual native/STEP; no repair'})
    print(len(results),'native negative cases rejected')
if __name__=='__main__':main()
