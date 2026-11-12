"""Independent exact-partition/native audit of C8fbbef0. Does not import feed_power.
Usage: native_probe.py MATERIALIZED_GIT_ROOT OUTPUT_JSON
"""
import collections,gzip,itertools,json,math,sys
from fractions import Fraction as Q
from functools import lru_cache
from pathlib import Path
R=Path(sys.argv[1]).resolve();sys.path.insert(0,str(R/'cad/layout'));sys.path.append('/usr/lib/freecad-python3/lib')
import FreeCAD as App
from cad_validation import check_cad_adapter
from layout_common import load,selected,bounds,config
D=load(R/'cad/feed_power/inputs.assumed.json');O=load(R/'cad/frame_mount/inputs.assumed.json');P=R/'cad/build/feed_power';oldP=R/'cad/build/frame_mount'
valid=check_cad_adapter(D,P,R/'cad/feed_power/inputs.assumed.json')
def packed(p):return json.loads(gzip.decompress(p.read_bytes()))
S=packed(P/'raw_checked_tool/all_pairs.json.gz')+packed(P/'service_scenes.json.gz');OS=packed(oldP/'raw_checked_tool/all_pairs.json.gz')+packed(oldP/'service_scenes.json.gz')
oldby={c['id']:c for c in O['components']};changed={c['id'] for c in D['components'] if c['id'] not in oldby or bounds(D,c)!=bounds(O,oldby[c['id']])}
LEG={tuple(sorted(('doser_slide',n))) for n in ('hopper_R','hopper_floor_right','receiving_rim_right')}
FRAME={tuple(sorted(p)) for p in [('crossbar'+str(i),s) for i in range(3) for s in ('side_rail_L','side_rail_R')]+[('crossbar0','cylinder_mount_rear'),('crossbar2','output_support'),('cylinder_barrel','cylinder_mount_front')]}
GATE={tuple(sorted(p)) for p in [('inlet_gate','pocket_R'),('inlet_gate','pocket_R_lower'),('lock','guard_right'),('lock','stop_support'),('lock','stop_support_L'),('end_stop','guard_right'),('end_stop','stop_support'),('end_stop','stop_support_L')]}
oldcrit={'crossbar0','crossbar1','crossbar2','cylinder_mount_front','cylinder_mount_rear','cylinder_seat_L','cylinder_seat_R','cylinder_seat_bridge',*[f'upper_post_{s}{i}' for s in 'LR' for i in range(3)],'inlet_gate','gate_service_cap','gate_house_front','gate_house_rear','gate_house_top','pocket_R_lower','lock','end_stop','stop_support','stop_support_L','stop_support_bridge','guard_right'}
def key(b):return tuple(tuple(b.get(k)) if b.get(k) is not None else None for k in ('lo','hi','delta'))+(b.get('motion'),)
@lru_cache(None)
def solve(a,b):
 if a[3]!='linear' or b[3]!='linear' or a[2] is None or b[2] is None:return ('INDETERMINATE',None)
 expr=[];ev={Q(0),Q(1)}
 for i in range(3):
  expr.extend([(Q(a[1][i])-Q(b[0][i]),Q(a[2][i])-Q(b[2][i])),(Q(b[1][i])-Q(a[0][i]),Q(b[2][i])-Q(a[2][i]))])
 for c,d in expr:
  if d and 0<=-c/d<=1:ev.add(-c/d)
 ev=sorted(ev)
 for u in ev+[(a+b)/2 for a,b in zip(ev,ev[1:])]:
  if all(c+d*u>0 for c,d in expr):return ('POSITIVE_BOUND_OVERLAP',str(u))
 return ('NO_POSITIVE_VOLUME',None)
docs={};obs={};odocs={};oobs={}
for v in 'AB':
 docs[v]=App.openDocument(str(P/v/f'layout_{v}.FCStd'));obs[v]={o.Name:o for o in docs[v].Objects if hasattr(o,'ResearchStatus')}
 odocs[v]=App.openDocument(str(oldP/v/f'layout_{v}.FCStd'));oobs[v]={o.Name:o for o in odocs[v].Objects if hasattr(o,'ResearchStatus')}
cache={}
def native(v,pair,state,u,old=False):
 objs=oobs[v] if old else obs[v];positions=[tuple(Q(x)+u*Q(d) for x,d in zip(state[n]['lo'],state[n]['delta'])) for n in pair];k=(v,old,tuple(pair),tuple(positions))
 if k not in cache:
  shapes=[]
  for n,pos in zip(pair,positions):
   sh=objs[n].Shape.copy();bb=sh.optimalBoundingBox(False,False);sh.translate(App.Vector(*[float(x)*1000-y for x,y in zip(pos,(bb.XMin,bb.YMin,bb.ZMin))]));shapes.append(sh)
  cache[k]=shapes[0].common(shapes[1]).Volume
 return cache[k]
res={'C':'8fbbef00023e146e32cb6ff290a0c19408ca13b5','native_adapter':valid,'all_pair_rows':0,'critical_counts':collections.Counter(),'gate_target_counts':collections.Counter(),'frame_target_counts':collections.Counter(),'new_service_counts':collections.Counter(),'unexpected_positive':[],'native_positive_pairs':{},'legacy_rows':[],'service_continuity':[],'new_service_composition':[],'before_after_20':[]}
dimensions=set();lookup={};olo={(s['variant'],s['case'],st['phase']):st for s in OS for st in s['stages']}
for s in S:
 v=s['variant']
 for st in s['stages']:
  state=st['state'];lookup[(v,s['case'],st['phase'])]=st;expected=list(itertools.combinations(sorted(state),2));assert [tuple(r['pair']) for r in st['pairs']]==expected,(v,s['case'],st['phase'],'pair coverage');res['all_pair_rows']+=len(expected)
  for n,b in state.items():
   if n=='research_obstacle':continue
   dk=(v,n,tuple(b['lo']),tuple(b['hi']))
   if dk in dimensions:continue
   bb=obs[v][n].Shape.optimalBoundingBox(False,False);assert all(math.isclose(float(Q(y)-Q(x))*1000,z,rel_tol=1e-11,abs_tol=1e-8) for x,y,z in zip(b['lo'],b['hi'],(bb.XLength,bb.YLength,bb.ZLength))),(v,n,'native dimensions');dimensions.add(dk)
  for pair in expected:
   a,b=pair;status,u=solve(key(state[a]),key(state[b]));critical=bool(set(pair)&(changed|oldcrit|{'doser_slide','pump_motor','hydraulic_tank'})) or pair in GATE or pair in LEG
   if critical:res['critical_counts'][status]+=1
   if pair in GATE:res['gate_target_counts'][status]+=1
   if pair in FRAME:res['frame_target_counts'][status]+=1
   moving=any(body['delta'] is not None and any(Q(x)!=0 for x in body['delta']) for body in (state[a],state[b]))
   if s['case'].startswith('service_fp_') and moving:res['new_service_counts'][status]+=1
   if status!='POSITIVE_BOUND_OVERLAP':continue
   if 'research_obstacle' in pair:continue
   volume=native(v,pair,state,Q(u))
   row={'variant':v,'case':s['case'],'phase':st['phase'],'pair':list(pair),'u':u,'native_common_mm3':volume}
   if volume>1e-5:res['native_positive_pairs'].setdefault(v+'|'+a+'|'+b,row)
   if s['case']=='service_doser_slide' and pair in LEG:res['legacy_rows'].append(row)
   else:res['unexpected_positive'].append(row)
 if s['case'].startswith('service_'):
  ids=set(s['stages'][0]['state']);ok=True
  for l,r in zip(s['stages'],s['stages'][1:]):
   ok=ok and Q(l['time'][1])==Q(r['time'][0]) and set(l['state'])==set(r['state'])==ids
   for n in l['state']:
    ok=ok and all(Q(x)+Q(d)==Q(y) for k in ('lo','hi') for x,d,y in zip(l['state'][n][k],l['state'][n]['delta'],r['state'][n][k]))
  first,last=s['stages'][0]['state'],s['stages'][-1]['state'];restored=set(first)==set(last) and all(first[n]['lo']==last[n]['lo'] and first[n]['hi']==last[n]['hi'] and last[n]['delta']==['0','0','0'] for n in ids);assert ok and restored
  res['service_continuity'].append({'variant':v,'case':s['case'],'continuous':ok,'restored':restored,'all_body_ids_retained':True})
  if s['case'].startswith('service_fp_'):
   lift=config(D,'service_lift');side=config(D,'doser_service_y');park=config(D,'motor_park_y');module=('pump_motor','motor_mount_rear','motor_mount_front')
   def mv(names,axis,dist):return {n:tuple(dist if i==axis else Q(0) for i in range(3)) for n in names}
   plans={'service_fp_doser_retract_lift':[mv(['doser_slide'],1,side),mv(['doser_slide'],2,lift),mv(['doser_slide'],2,-lift),mv(['doser_slide'],1,-side)],'service_fp_motor':[mv(['pump_motor'],2,lift),mv(['pump_motor'],2,-lift)],'service_fp_powerpack_module':[mv(('hydraulic_tank',*module),2,lift),mv(('hydraulic_tank',*module),2,-lift)],'service_fp_tank_after_motor_park':[mv(module,2,lift),mv(module,1,park),mv(['hydraulic_tank'],2,lift),mv(['hydraulic_tank'],2,-lift),mv(module,1,-park),mv(module,2,-lift)]}
   expected=[{}]+plans[s['case']]+[{}];assert len(expected)==len(s['stages'])
   moves=[]
   for st,plan in zip(s['stages'],expected):
    observed={n:tuple(map(Q,b['delta'])) for n,b in st['state'].items() if any(Q(d)!=0 for d in b['delta'])};assert observed==plan,(v,s['case'],st['phase'],'unexpected moving composition/delta');moves.append({n:list(map(str,d)) for n,d in observed.items()})
   res['new_service_composition'].append({'variant':v,'case':s['case'],'moves':moves,'initial_and_final_registry_matches_input':ids=={c['id'] for c in selected(D,v)}})
# Same historic witness state/time for all 20 original pairs.
for row in json.loads((R/'verification/r4_feed_power/before_inventory.json').read_text())['rows']:
 w=next(w for w in row['native_representatives'] if w.get('common_volume_mm3',0)>1e-5);v=row['variant'];p=row['pair'];old=olo[(v,w['case'],w['phase'])];new=lookup[(v,w['case'],w['phase'])];u=(Q(w['time'])-Q(old['time'][0]))/(Q(old['time'][1])-Q(old['time'][0]));assert old['time']==new['time']
 bv=native(v,p,old['state'],u,True);av=native(v,p,new['state'],u);legacy=tuple(p) in LEG;assert bv>1e-5 and (av>1e-5)==legacy
 res['before_after_20'].append({'variant':v,'pair':p,'case':w['case'],'phase':w['phase'],'time':w['time'],'before_native_mm3':bv,'after_native_mm3':av,'disposition':'BLOCKED_LEGACY_UP' if legacy else 'STATIC_REMOVED'})
# Native opposing planar faces, independently of the new contact reporter.
def area(a,b):
 result=0.
 for f in a.Faces:
  if 'Plane' not in type(f.Surface).__name__:continue
  for g in b.Faces:
   if 'Plane' in type(g.Surface).__name__ and f.normalAt(0,0).dot(g.normalAt(0,0))<-0.999999999 and f.distToShape(g)[0]<1e-8:result+=f.common(g).Area
 return result
res['new_interfaces']=[];res['preserved_frame_interfaces']=[]
for f,field,total in [(P/'interfaces.json','new_interfaces',62),(R/'verification/r4_feed_power/previous_frame_interfaces.json','preserved_frame_interfaces',58)]:
 js=json.loads(f.read_text());js=js['native_interfaces'] if isinstance(js,dict) else js;assert len(js)==total and len({(x['variant'],tuple(x['pair'])) for x in js})==total
 for j in js:
  v=j['variant'];a,b=j['pair'];ar=area(obs[v][a].Shape,obs[v][b].Shape);vol=obs[v][a].Shape.common(obs[v][b].Shape).Volume;assert ar>0 and vol<=1e-5;res[field].append({'variant':v,'pair':[a,b],'opposing_planar_face_area_mm2':ar,'common_mm3':vol})
# Prove true coplanar lower support and both guides along the horizontal Y path.
res['doser_support']=[]
for s in S:
 if s['case']!='service_fp_doser_retract_lift':continue
 for st in (s['stages'][1],s['stages'][-2]):
  b=st['state']['doser_slide'];floors=[st['state'][n] for n in ('doser_floor_left','doser_floor_right','doser_tray_inner','doser_tray_outer')];guides=[st['state'][n] for n in ('doser_guide_L_inner','doser_guide_L_outer','doser_guide_R_inner','doser_guide_R_outer')];events={Q(0),Q(1)};dy=Q(b['delta'][1]);assert dy
  for support in floors+guides:
   for k in ('lo','hi'):
    for e in ('lo','hi'):
     u=(Q(support[k][1])-Q(b[e][1]))/dy
     if 0<=u<=1:events.add(u)
  events=sorted(events);tests=events+[(x+y)/2 for x,y in zip(events,events[1:])];lower=[];left=[];right=[]
  for u in tests:
   lo=[Q(x)+u*Q(d) for x,d in zip(b['lo'],b['delta'])];hi=[Q(x)+u*Q(d) for x,d in zip(b['hi'],b['delta'])]
   def ar(f,axes):return max(Q(0),min(hi[axes[0]],Q(f['hi'][axes[0]]))-max(lo[axes[0]],Q(f['lo'][axes[0]])))*max(Q(0),min(hi[axes[1]],Q(f['hi'][axes[1]]))-max(lo[axes[1]],Q(f['lo'][axes[1]])))
   lower.append(sum(ar(f,(0,1)) for f in floors if Q(f['hi'][2])==lo[2]));left.append(sum(ar(g,(1,2)) for g in guides if Q(g['hi'][0])==lo[0]));right.append(sum(ar(g,(1,2)) for g in guides if Q(g['lo'][0])==hi[0]))
  assert min(lower)>0 and min(left)>0 and min(right)>0
  res['doser_support'].append({'variant':s['variant'],'phase':st['phase'],'minimum_lower_m2':str(min(lower)),'minimum_left_guide_m2':str(min(left)),'minimum_right_guide_m2':str(min(right)),'method':'all exact support-edge events and open interiors; coplanar faces required','hardware_capacity':'UNKNOWN'})
# Raw registry preserves every non-CLEAR class and context, not only six examples.
raw=collections.defaultdict(lambda:{'classes':collections.Counter(),'contexts':set()})
with gzip.open(P/'classifications.jsonl.gz','rt') as f:
 for line in f:
  x=json.loads(line)
  if x['class']=='CLEAR':continue
  r=raw[(x['variant'],tuple(x['pair']))];r['classes'][x['class']]+=1;r['contexts'].add((x['case'],x['phase']))
inv=json.loads((P/'inventory/inventory.json').read_text());by={(r['variant'],tuple(r['pair'])):r for r in inv['rows']};assert set(by)==set(raw)
for k,r in by.items():assert raw[k]['classes']==r['classes'] and raw[k]['contexts']=={(c['case'],c['phase']) for c in r['contexts']}
rem=[r for r in inv['rows'] if r['classification']=='NATIVE_PENETRATION'];assert len(rem)==6 and all(tuple(r['pair']) in LEG and r['disposition']=='BLOCKED_LEGACY_STRAIGHT_UP' for r in rem);assert set(res['native_positive_pairs'])=={r['variant']+'|'+'|'.join(r['pair']) for r in rem}
res['registry_rows']=len(by);res['registry_summary']=inv['summary'];res['native_unique_pose_checks']=len(cache);res['native_dimension_states']=len(dimensions);res['new_moving_positive_rows']=res['new_service_counts'].get('POSITIVE_BOUND_OVERLAP',0)
assert not res['unexpected_positive'] and res['new_moving_positive_rows']==0 and len(res['legacy_rows'])==12 and all(r['native_common_mm3']>1e-5 for r in res['legacy_rows'])
assert res['all_pair_rows']==638919 and sum(res['critical_counts'].values())==507043 and len(res['service_continuity'])==22 and len(res['new_service_composition'])==8
Path(sys.argv[2]).write_text(json.dumps(res,indent=2)+'\n')
for dd in (docs,odocs):
 for d in dd.values():App.closeDocument(d.Name)
print('PASS',res['all_pair_rows'],dict(res['critical_counts']),'static',sum(r['disposition']=='STATIC_REMOVED' for r in res['before_after_20']),'legacy',len(res['legacy_rows']),'new moving positive',res['new_moving_positive_rows'])
