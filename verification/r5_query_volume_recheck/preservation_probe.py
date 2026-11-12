import sys,json,subprocess,gzip,hashlib,math
from pathlib import Path
sys.path.append('/usr/lib/freecad-python3/lib');import FreeCAD as App
sys.path.insert(0,sys.argv[1]+'/cad/layout');from layout_common import load;from cad_validation import check_cad_adapter
root=Path(sys.argv[1]);ip=root/'cad/layout/conditional_inputs.assumed.json';models=root/'cad/build/research_layout';native=check_cad_adapter(load(ip),models,ip);result={'pristine_native':{v:{'status':native[v]['status'],'queries':native[v]['query_volumes'],'count':native[v]['query_count']} for v in 'AB'},'native_query_unchanged':{}}
def signatures(path):
 d=App.openDocument(str(path));d.recompute();r={}
 for n in ('CylinderRemoval','DoserRemoval'):
  o=d.getObject(n);b=o.Shape.optimalBoundingBox(False,False);r[n]=[o.Length.Value,o.Width.Value,o.Height.Value,*list(o.Placement.toMatrix().A),*list(o.getGlobalPlacement().toMatrix().A),o.Shape.Volume]+[getattr(b,k) for k in ('XMin','YMin','ZMin','XMax','YMax','ZMax')]
 App.closeDocument(d.Name);return r
for v in 'AB':
 old=signatures('/tmp/rev-query-old-'+v+'.FCStd');new=signatures(models/v/f'layout_{v}.FCStd');result['native_query_unchanged'][v]={n:all(math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-8) for a,b in zip(old[n],new[n])) for n in old};assert all(result['native_query_unchanged'][v].values())
def blob(c,p):return subprocess.check_output(['git','show',c+':'+p],cwd=root)
# source root must be the review checkout with Git; compared implementation remains exact C.
a='5449fb9bc4c20fcbc40fdec932876dcecc90ef4d';b='de377f012da08f34796b2e59aee663ba0b2b3d2b';result['immutable']={p:blob(a,p)==blob(b,p) for p in ('cad/layout/build_model.py','cad/layout/conditional_inputs.assumed.json','cad/layout/layout_lifecycle.py','params/registry.yaml')};result['variants']={}
for v in 'AB':result['variants'][v]={'objects_equal':json.loads(blob(a,f'cad/build/research_layout/{v}/manifest.json'))['objects']==json.loads(blob(b,f'cad/build/research_layout/{v}/manifest.json'))['objects'],'png_equal':{n:blob(a,f'cad/build/research_layout/{v}/{n}.png')==blob(b,f'cad/build/research_layout/{v}/{n}.png') for n in ('isometric','front','side','top')}}
x=json.loads(gzip.decompress(blob(a,'cad/build/research_layout/checks/all_pairs.json.gz')));y=json.loads(gzip.decompress(blob(b,'cad/build/research_layout/checks/all_pairs.json.gz')));result['all_phase_states_and_pair_evidence_equal']=[s['stages'] for s in x]==[s['stages'] for s in y];result['pair_rows']=sum(len(st['pairs']) for s in y for st in s['stages']);Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+'\n');print(result['native_query_unchanged'],result['immutable'],result['all_phase_states_and_pair_evidence_equal'])
