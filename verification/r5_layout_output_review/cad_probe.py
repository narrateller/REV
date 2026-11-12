import sys,json,gzip,itertools,hashlib,os,math,tempfile
from pathlib import Path
sys.path.append('/usr/lib/freecad-python3/lib')
import FreeCAD as App,Part
root=Path(sys.argv[1]);data=json.loads((root/'cad/layout/conditional_inputs.assumed.json').read_text());scenes=json.load(gzip.open(root/'cad/build/research_layout/checks/all_pairs.json.gz','rt'));out={}
for v in 'AB':
 path=root/f'cad/build/research_layout/{v}';doc=App.openDocument(str(path/f'layout_{v}.FCStd'));doc.recompute();obs={x.Name:x for x in doc.Objects if hasattr(x,'ResearchStatus')};manifest=json.loads((path/'manifest.json').read_text());byid={x['id']:x for x in manifest['objects']}
 valid=all(x.Shape.isValid() for x in obs.values()); errors=[abs(getattr(x.Shape.optimalBoundingBox(False,False),k)-y) for n,x in obs.items() for k,y in zip(('XMin','YMin','ZMin','XMax','YMax','ZMax'),byid[n]['cad_bounds_mm'])];bounds_match=max(errors)<1e-9
 sys.path.insert(0,str(root/'cad/layout'));from build_model import render;from layout_common import config
 with tempfile.TemporaryDirectory() as rt:
  render(doc,list(obs.values()),Path(rt),v,float(config(data,'tessellation'))*1000);images={n:(Path(rt)/(n+'.png')).read_bytes()==(path/(n+'.png')).read_bytes() for n in ('isometric','front','side','top')}
 components=[x for x in data['components'] if x['variant'] in ('both',v)];c=next(x for x in components if x['id']=='cylinder_barrel');key=c['radius'];idx=list(data['parameters']).index(key)+1;old=doc.Inputs.get('B'+str(idx));rad=obs['cylinder_barrel'].Radius.Value;doc.Inputs.set('B'+str(idx),'='+str(float(data['parameters'][key]['value'])*1.1)+' m');doc.recompute();edited=obs['cylinder_barrel'].Radius.Value;doc.Inputs.set('B'+str(idx),'='+data['parameters'][key]['value']+' m');doc.recompute()
 step=Part.read(str(path/f'layout_{v}.step'));volumes=sorted(round(x.Shape.Volume,5) for x in obs.values());stepvol=sorted(round(x.Volume,5) for x in step.Solids)
 st=next(x for x in scenes if x['variant']==v and x['case']=='sufficient')['stages'][0];cases=[]
 for row in st['pairs']:
  if row['status'] not in ('COLLISION','INDETERMINATE'):continue
  a,b=row['pair'];common=obs[a].Shape.common(obs[b].Shape);cases.append({'pair':[a,b],'adapter':row['status'],'common_volume_mm3':common.Volume,'common_faces':len(common.Faces),'common_edges':len(common.Edges),'distance_mm':obs[a].Shape.distToShape(obs[b].Shape)[0]})
 out[v]={'objects':len(obs),'valid':valid,'bounds_match_manifest':bounds_match,'max_bound_serialization_difference_mm':max(errors),'reopened_render_png_matches':images,'step_valid':step.isValid(),'step_solids':len(step.Solids),'step_volume_multiset_matches':volumes==stepvol,'radius_edit':{'parameter':key,'before_mm':rad,'edited_mm':edited,'restored_mm':obs['cylinder_barrel'].Radius.Value,'passed':abs(edited-1.1*rad)<1e-8},'static_brep_cases':cases};App.closeDocument(doc.Name)
Path(sys.argv[2]).write_text(json.dumps(out,indent=2)+'\n');print({v:{k:x for k,x in r.items() if k!='static_brep_cases'} for v,r in out.items()})
