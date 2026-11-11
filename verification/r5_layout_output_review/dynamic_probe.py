import sys,json,gzip
from fractions import Fraction as F
from pathlib import Path
sys.path.append('/usr/lib/freecad-python3/lib');import FreeCAD as App
root=Path(sys.argv[1]);scenes=json.load(gzip.open(root/'cad/build/research_layout/checks/all_pairs.json.gz','rt'));result=[]
for v in 'AB':
 doc=App.openDocument(str(root/f'cad/build/research_layout/{v}/layout_{v}.FCStd'));obs={o.Name:o for o in doc.Objects if hasattr(o,'ResearchStatus')};seen=set()
 for st in next(s for s in scenes if s['variant']==v and s['case']=='sufficient')['stages']:
  for row in st['pairs']:
   a,b=row['pair'];key=tuple(row['pair'])
   if row['status']!='COLLISION' or key in seen or not any(F(x)!=0 for n in (a,b) for x in st['state'][n]['delta']):continue
   candidates=[x for x in row['evidence']['segments'] if x['collision_status']=='COLLISION' and x['interval']=='open']
   if not candidates:continue
   seg=candidates[0];t=(F(seg['from'])+F(seg['to']))/2;u=(t-F(st['time'][0]))/(F(st['time'][1])-F(st['time'][0]));shapes=[]
   for n in (a,b):
    sh=obs[n].Shape.copy();bb=sh.optimalBoundingBox(False,False);base=(bb.XMin,bb.YMin,bb.ZMin);state=st['state'][n];lo=[F(x)+u*F(d) for x,d in zip(state['lo'],state['delta'])];sh.translate(App.Vector(*[float(x)*1000-y for x,y in zip(lo,base)]));shapes.append(sh)
   common=shapes[0].common(shapes[1]);result.append({'variant':v,'phase':st['phase'],'pair':[a,b],'sample_time':str(t),'common_volume_mm3':common.Volume,'common_faces':len(common.Faces),'distance_mm':shapes[0].distToShape(shapes[1])[0]});seen.add(key)
 App.closeDocument(doc.Name)
Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+'\n');print(result)
