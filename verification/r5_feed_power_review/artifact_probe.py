"""Read saved native models, rerender, edit new nodes, compare actual rebuilds."""
import hashlib,json,math,sys,tempfile
from pathlib import Path
R=Path(sys.argv[1]).resolve();copy=Path(sys.argv[2]).resolve();sys.path.insert(0,str(R/'cad/layout'));sys.path.append('/usr/lib/freecad-python3/lib')
import FreeCAD as App
from build_model import render
from layout_common import load,selected,config
from cad_validation import check_cad_adapter
D=load(R/'cad/feed_power/inputs.assumed.json');o=R/'cad/build/feed_power';b=copy/'cad/build/feed_power';result={}
for v in 'AB':
 d=App.openDocument(str(o/v/f'layout_{v}.FCStd'));d.recompute();obs=[x for x in d.Objects if hasattr(x,'ResearchStatus')];ids={x.Name for x in obs};assert ids=={x['id'] for x in selected(D,v)}
 with tempfile.TemporaryDirectory() as tmp:
  render(d,obs,Path(tmp),v,float(config(D,'tessellation'))*1000)
  png={p:(Path(tmp)/(p+'.png')).read_bytes()==(o/v/(p+'.png')).read_bytes() for p in ('front','side','top','isometric')}
 edits=[]
 for name in ('motor_mount_rear','doser_tray_inner','tank_arm_0'):
  c=next(x for x in D['components'] if x['id']==name);ref=c['size'][2];idx=list(D['parameters']).index(ref)+1;orig=D['parameters'][ref]['value'];obj=d.getObject(name);start=obj.Height.Value
  d.Inputs.set('B'+str(idx),'='+str(float(orig)*1.1)+' m');d.recompute();after=obj.Height.Value
  assert math.isclose(after,start*1.1,abs_tol=1e-8);d.Inputs.set('B'+str(idx),'='+orig+' m');d.recompute();assert math.isclose(obj.Height.Value,start,abs_tol=1e-8)
  edits.append({'id':name,'parameter':ref,'before_mm':start,'edited_mm':after,'restored_mm':obj.Height.Value})
 m=json.loads((o/v/'manifest.json').read_text());n=json.loads((b/v/'manifest.json').read_text());semantic={k:m[k]==n[k] for k in ('objects','input_sha256','reopen_recompute','edit_probe','spreadsheet_parameters','query_volumes')}
 rebuiltpng={p:(o/v/(p+'.png')).read_bytes()==(b/v/(p+'.png')).read_bytes() for p in png};assert all(png.values()) and all(semantic.values()) and all(rebuiltpng.values())
 result[v]={'saved_native_rerender_png':png,'rebuild_semantic_manifest':semantic,'rebuild_png':rebuiltpng,'body_count':len(ids),'edits':edits,'all_valid':all(x.Shape.isValid() and not x.Shape.isNull() for x in obs)};App.closeDocument(d.Name)
result['rebuilt_native_adapter']=check_cad_adapter(D,b,R/'cad/feed_power/inputs.assumed.json')
details={p:(o/p).read_bytes()==(b/p).read_bytes() for n in ('doser_mount_before_after','doser_service_before_after','powerpack_before_after') for p in (n+'.svg',n+'.png')};result['regenerated_detail_figures']=details;assert all(details.values())
Path(sys.argv[3]).write_text(json.dumps(result,indent=2)+'\n');print('PASS: saved/rebuilt FP native models, QueryVolumes, 8 PNG, 6 detail figures and 6 spreadsheet edits')
