import sys,json,gzip,itertools,subprocess,hashlib,math
from pathlib import Path
from fractions import Fraction as F
sys.path.insert(0,sys.argv[1]+'/cad/layout');sys.path.append('/usr/lib/freecad-python3/lib')
import FreeCAD as App
from cad_validation import check_cad_adapter
from layout_common import load
root=Path(sys.argv[1]);ip=root/'cad/layout_correction/inputs.assumed.json';data=load(ip);outdir=root/'cad/build/layout_correction';valid=check_cad_adapter(data,outdir,ip)
scenes=json.load(gzip.open(outdir/'raw_checked_tool/all_pairs.json.gz','rt'))+json.load(gzip.open(outdir/'service_scenes.json.gz','rt'))
targets={tuple(sorted(x)) for x in [('inlet_gate','pocket_R'),('inlet_gate','pocket_R_lower'),('lock','guard_right'),('lock','stop_support'),('lock','stop_support_L'),('end_stop','guard_right'),('end_stop','stop_support'),('end_stop','stop_support_L')]}
critical={'inlet_gate','gate_service_cap','lock','end_stop','stop_support','stop_support_L','stop_support_bridge','guard_right'}
def interval(a,b):
 lo,hi=F(0),F(1)
 for i in range(3):
  for c,v in ((F(a['hi'][i])-F(b['lo'][i]),F(a['delta'][i])-F(b['delta'][i])),(F(b['hi'][i])-F(a['lo'][i]),F(b['delta'][i])-F(a['delta'][i]))):
   if not v:
    if c<=0:return None
   elif v>0:lo=max(lo,-c/v)
   else:hi=min(hi,-c/v)
 if lo<hi:return [str(lo),str(hi)]
 if lo==hi and all(F(a['hi'][i])+lo*F(a['delta'][i])>F(b['lo'][i])+lo*F(b['delta'][i]) and F(b['hi'][i])+lo*F(b['delta'][i])>F(a['lo'][i])+lo*F(a['delta'][i]) for i in range(3)):return [str(lo),str(hi)]
 return None
result={'targets':[],'other_critical_positive':[],'other_critical_curved_envelopes':[],'coverage_errors':[],'pair_rows':0,'native_checks':0,'native_positive':[],'native_body_counts':{v:valid[v]['solid_count'] for v in 'AB'}};docs={};obs={};cache={}
for v in 'AB':
 docs[v]=App.openDocument(str(outdir/v/f'layout_{v}.FCStd'));obs[v]={o.Name:o for o in docs[v].Objects if hasattr(o,'ResearchStatus')}
for scene in scenes:
 v=scene['variant']
 for st in scene['stages']:
  pairs=[tuple(r['pair']) for r in st['pairs']];expected=list(itertools.combinations(sorted(st['state']),2));result['pair_rows']+=len(pairs)
  if pairs!=expected:result['coverage_errors'].append([v,scene['case'],st['phase']])
  for a,b in pairs:
   ba,bb=st['state'][a],st['state'][b];target=(a,b) in targets
   if not target and not ({a,b}&critical):continue
   if ba.get('delta') is None or bb.get('delta') is None:
    if target:result['targets'].append({'variant':v,'case':scene['case'],'phase':st['phase'],'pair':[a,b],'status':'INDETERMINATE'})
    continue
   assert ba['motion']==bb['motion']=='linear'
   overlap=interval(ba,bb)
   entry={'variant':v,'case':scene['case'],'phase':st['phase'],'pair':[a,b],'strict_overlap_normalized':overlap,'exact_boxes':ba['exact_box'] and bb['exact_box']}
   if target:
    assert entry['exact_boxes'] and overlap is None,entry
    # Native primitives must agree with nominal box extents, then exact inequalities cover the whole translation.
    for name in (a,b):
     state=st['state'][name];shape=obs[v][name].Shape;bounds=shape.optimalBoundingBox(False,False)
     assert all(math.isclose(float(F(hi)-F(lo))*1000,x,rel_tol=1e-10,abs_tol=1e-8) for lo,hi,x in zip(state['lo'],state['hi'],(bounds.XLength,bounds.YLength,bounds.ZLength)))
    samples=[]
    for u in (F(0),F(1,2),F(1)):
     positions=[tuple(F(x)+u*F(d) for x,d in zip(st['state'][n]['lo'],st['state'][n]['delta'])) for n in (a,b)];key=(v,a,b,tuple(positions))
     if key not in cache:
      shapes=[]
      for n,pos in zip((a,b),positions):
       shape=obs[v][n].Shape.copy();bbx=shape.optimalBoundingBox(False,False);shape.translate(App.Vector(*[float(x)*1000-y for x,y in zip(pos,(bbx.XMin,bbx.YMin,bbx.ZMin))]));shapes.append(shape)
      cache[key]=shapes[0].common(shapes[1]).Volume
     vol=cache[key];samples.append(vol)
     if vol>1e-5:result['native_positive'].append([entry,str(u),vol])
    entry['native_start_mid_end_volumes_mm3']=samples;result['targets'].append(entry)
   elif overlap:
    result['other_critical_positive' if entry['exact_boxes'] else 'other_critical_curved_envelopes'].append(entry)
result['service_continuity_independent']=[]
for scene in scenes:
 if not scene['case'].startswith('service_'):continue
 okay=True
 for left,right in zip(scene['stages'],scene['stages'][1:]):
  okay=okay and F(left['time'][1])==F(right['time'][0]) and set(left['state'])==set(right['state'])
  for n in left['state']:
   for bound in ('lo','hi'):
    okay=okay and all(F(x)+F(d)==F(y) for x,d,y in zip(left['state'][n][bound],left['state'][n]['delta'],right['state'][n][bound]))
 first,last=scene['stages'][0]['state'],scene['stages'][-1]['state']
 restored=all(all(F(x)==F(y) for key in ('lo','hi') for x,y in zip(first[n][key],last[n][key])) for n in first)
 result['service_continuity_independent'].append({'variant':scene['variant'],'case':scene['case'],'continuous':okay,'restored':restored});assert okay and restored
result['native_checks']=len(cache)
result['remaining_native_static']=[]
for v in 'AB':
 for a,b in [('cylinder_barrel','cylinder_mount_front'),('hydraulic_tank','pump_motor'),('crossbar0','side_rail_L')]:
  common=obs[v][a].Shape.common(obs[v][b].Shape);result['remaining_native_static'].append({'variant':v,'pair':[a,b],'common_volume_mm3':common.Volume})
for d in docs.values():App.closeDocument(d.Name)
# Compare all original IDs and frozen file bytes against actual Git objects, not only frozen manifest claims.
def blob(c,p):return subprocess.check_output(['git','show',c+':'+p],cwd=root)
frozen=json.loads((root/'verification/r4_layout_correction/frozen_tool.json').read_text());base='de377f012da08f34796b2e59aee663ba0b2b3d2b';current='120a9582f4835e81cdf324605a14f632ce7db2cb';result['frozen_files']={p:blob(base,p)==blob(current,p) and hashlib.sha256(blob(current,p)).hexdigest()==h for p,h in frozen['sha256'].items()};old=json.loads(blob(base,'cad/layout/conditional_inputs.assumed.json'));result['inventory']={}
for v in 'AB':
 before={c['id'] for c in old['components'] if c['variant'] in ('both',v)};after={c['id'] for c in data['components'] if c['variant'] in ('both',v)};result['inventory'][v]={'before':len(before),'after':len(after),'removed':sorted(before-after),'added':sorted(after-before)}
assert not result['native_positive'] and not result['coverage_errors'] and all(result['frozen_files'].values())
Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k not in ('targets','other_critical_positive','other_critical_curved_envelopes')});print('target rows',len(result['targets']),'other strict overlap',len(result['other_critical_positive']),'curve envelope overlap',len(result['other_critical_curved_envelopes']))
