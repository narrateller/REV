import sys,json,tempfile,hashlib
from pathlib import Path
sys.path.append('/usr/lib/freecad-python3/lib');import FreeCAD as App
root=Path(sys.argv[1]);sys.path.insert(0,str(root/'cad/layout'));from build_model import render;from layout_common import config,load
p=root/'cad/build/layout_correction';data=load(root/'cad/layout_correction/inputs.assumed.json');result={}
for v in 'AB':
 d=App.openDocument(str(p/v/f'layout_{v}.FCStd'));d.recompute();objs=[x for x in d.Objects if hasattr(x,'ResearchStatus')]
 with tempfile.TemporaryDirectory() as tmp:
  render(d,objs,Path(tmp),v,float(config(data,'tessellation'))*1000);png={n:(Path(tmp)/(n+'.png')).read_bytes()==(p/v/(n+'.png')).read_bytes() for n in ('isometric','front','top','side')}
 c=next(c for c in data['components'] if c['id']=='gate_house_top');ref=c['size'][2];cell='B'+str(list(data['parameters']).index(ref)+1);o=d.getObject(c['id']);before=o.Height.Value;value=data['parameters'][ref]['value'];d.Inputs.set(cell,'='+str(float(value)*1.1)+' m');d.recompute();after=o.Height.Value;d.Inputs.set(cell,'='+value+' m');d.recompute()
 result[v]={'bodies':len(objs),'all_valid':all(x.Shape.isValid() for x in objs),'native_rerender_png_identical':png,'new_body_spreadsheet_edit':{'ID':c['id'],'parameter':ref,'before_mm':before,'after_mm':after,'restored_mm':o.Height.Value}};assert all(png.values()) and abs(after-before*1.1)<1e-8
 App.closeDocument(d.Name)
run=json.loads((p/'run.json').read_text());result['artifact_hash_mismatches']=[name for name,h in run['artifacts'].items() if hashlib.sha256((p/name).read_bytes()).hexdigest()!=h];result['source_hash_mismatches']=[name for name,h in run['source_hashes'].items() if hashlib.sha256((root/name).read_bytes()).hexdigest()!=h];assert not result['artifact_hash_mismatches'] and not result['source_hash_mismatches'];Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+'\n');print(result)
