"""Independent R5 full-interval and native evidence for frame/mount C5198e01.
Usage: /usr/bin/python3 native_probe.py MATERIALIZED_GIT_ROOT OUTPUT_JSON
Never imports the new frame_mount report/classifier/inequality solver.
"""
import collections,copy,gzip,itertools,json,math,sys
from fractions import Fraction as Q
from functools import lru_cache
from pathlib import Path
R=Path(sys.argv[1]).resolve();sys.path.insert(0,str(R/'cad/layout'));sys.path.append('/usr/lib/freecad-python3/lib')
import FreeCAD as App
from cad_validation import check_cad_adapter
from layout_common import load,bounds,selected
D=load(R/'cad/frame_mount/inputs.assumed.json');O=load(R/'cad/layout_correction/inputs.assumed.json');out=R/'cad/build/frame_mount'
valid=check_cad_adapter(D,out,R/'cad/frame_mount/inputs.assumed.json')
S=json.loads(gzip.decompress((out/'raw_checked_tool/all_pairs.json.gz').read_bytes()))+json.loads(gzip.decompress((out/'service_scenes.json.gz').read_bytes()))
T={tuple(sorted(p)) for p in ([('crossbar'+str(i),rail) for i in range(3) for rail in ('side_rail_L','side_rail_R')]+[('crossbar0','cylinder_mount_rear'),('crossbar2','output_support'),('cylinder_barrel','cylinder_mount_front')])}
P={tuple(sorted(p)) for p in [('inlet_gate','pocket_R'),('inlet_gate','pocket_R_lower'),('lock','guard_right'),('lock','stop_support'),('lock','stop_support_L'),('end_stop','guard_right'),('end_stop','stop_support'),('end_stop','stop_support_L')]}
old={c['id']:c for c in O['components']};changed={c['id'] for c in D['components'] if c['id'] not in old or bounds(D,c)!=bounds(O,old[c['id']])}
# Independent event construction: evaluate exact signs at every zero and every
# open partition interior. Endpoints are evaluated explicitly, no native sampling CLEAR.
def canonical(b):return tuple(tuple(b.get(k)) if b.get(k) is not None else None for k in ('lo','hi','delta'))+(b.get('motion'),)
@lru_cache(None)
def solve(a,b):
 if a[3]!='linear' or b[3]!='linear' or a[2] is None or b[2] is None:return ('INDETERMINATE',None)
 expr=[];events={Q(0),Q(1)}
 for i in range(3):
  expr.extend([(Q(a[1][i])-Q(b[0][i]),Q(a[2][i])-Q(b[2][i])),(Q(b[1][i])-Q(a[0][i]),Q(b[2][i])-Q(a[2][i]))])
 for c,v in expr:
  if v and 0<=-c/v<=1:events.add(-c/v)
 events=sorted(events);tests=events+[(l+r)/2 for l,r in zip(events,events[1:])]
 for u in tests:
  if all(c+v*u>0 for c,v in expr):return ('POSITIVE_BOUND_OVERLAP',str(u))
 return ('NO_POSITIVE_VOLUME',None)
docs={};objects={};before_docs={};before_objects={}
for v in 'AB':
 docs[v]=App.openDocument(str(out/v/f'layout_{v}.FCStd'));objects[v]={o.Name:o for o in docs[v].Objects if hasattr(o,'ResearchStatus')}
 before_docs[v]=App.openDocument(str(R/f'cad/build/layout_correction/{v}/layout_{v}.FCStd'));before_objects[v]={o.Name:o for o in before_docs[v].Objects if hasattr(o,'ResearchStatus')}
cache={}
def native(v,pair,state,u,old=False):
 arr=before_objects if old else objects;shapes=[];key=[v,old,*pair]
 for n in pair:
  b=state[n]
  if b['delta'] is None:return None
  pos=tuple(Q(x)+u*Q(d) for x,d in zip(b['lo'],b['delta']));key.append(pos)
  sh=arr[v][n].Shape.copy();bb=sh.optimalBoundingBox(False,False);sh.translate(App.Vector(*[float(x)*1000-y for x,y in zip(pos,(bb.XMin,bb.YMin,bb.ZMin))]));shapes.append(sh)
 key=tuple(key)
 if key not in cache:cache[key]=shapes[0].common(shapes[1]).Volume
 return cache[key]
def initial(data,v):return {c['id']:{'lo':list(map(str,bounds(data,c)[0])),'hi':list(map(str,bounds(data,c)[1])),'delta':['0','0','0'],'motion':'linear'} for c in selected(data,v)}
result={'code_sha':'5198e0184b35978701ed1ce762d9e4fcd44997b3','native_adapter':valid,'changed_body_ids':sorted(changed),'all_pair_rows':0,'coverage_errors':[],'changed_counts':collections.Counter(),'prior_target_counts':collections.Counter(),'cylinder_service_counts':collections.Counter(),'target_counts':collections.Counter(),'target_rows':[],'positive_changed':[],'native_target_positive':[],'before_after':[],'services':[]}
# Native dimensions vs every state, including the boundary motion definitions.
secondary_counts=collections.Counter(); historical=[]
dims=set(); all_positive_native={}; bound_positive_controls=set(); curved_bound_candidates=set()
for s in S:
 v=s['variant']
 for st in s['stages']:
  ids=st['state'];expected=list(itertools.combinations(sorted(ids),2));pairs=[tuple(p['pair']) for p in st['pairs']];result['all_pair_rows']+=len(pairs)
  if pairs!=expected:result['coverage_errors'].append([v,s['case'],st['phase']])
  for n,b in ids.items():
   if n=='research_obstacle':continue
   key=(v,n,tuple(b['lo']),tuple(b['hi']))
   if key in dims:continue
   bb=objects[v][n].Shape.optimalBoundingBox(False,False)
   assert all(math.isclose(float(Q(y)-Q(x))*1000,z,rel_tol=1e-11,abs_tol=1e-8) for x,y,z in zip(b['lo'],b['hi'],(bb.XLength,bb.YLength,bb.ZLength))),(v,n,'native dimensions')
   dims.add(key)
  for a,b in expected:
   selected_pair=bool(changed&{a,b});prior=(a,b) in P;target=(a,b) in T
   cylinder=s['case'] in ('service_cylinder_barrel','service_rod','service_cylinder_module') and bool({'rod','cylinder_barrel'}&{a,b})
   status,w=solve(canonical(ids[a]),canonical(ids[b]))
   if (a,b) in {('guard_right','pump_motor'),('output_support','stop_support_bridge')}:
    secondary_counts[status]+=1
   if status=='POSITIVE_BOUND_OVERLAP':
    if a not in objects[v] or b not in objects[v]:bound_positive_controls.add((v,a,b))
    else:
     if not ids[a]['exact_box'] or not ids[b]['exact_box']:curved_bound_candidates.add((v,a,b))
     vol=native(v,(a,b),ids,Q(w))
     if vol>1e-5:all_positive_native.setdefault((v,a,b),{'variant':v,'pair':[a,b],'case':s['case'],'phase':st['phase'],'u':w,'native_volume_mm3':vol})
   if not(selected_pair or prior or target or cylinder):continue
   row={'variant':v,'case':s['case'],'phase':st['phase'],'pair':[a,b],'status':status,'witness_u':w}
   if selected_pair:
    result['changed_counts'][status]+=1
    if status=='POSITIVE_BOUND_OVERLAP':result['positive_changed'].append(row)
   if prior:result['prior_target_counts'][status]+=1
   if cylinder:result['cylinder_service_counts'][status]+=1
   if target:
    result['target_counts'][status]+=1;vols=[native(v,(a,b),ids,u) for u in (Q(0),Q(1,2),Q(1))];row['native_volumes_mm3']=vols;result['target_rows'].append(row)
    if any(x is not None and x>1e-5 for x in vols):result['native_target_positive'].append(row)
 if s['case'].startswith('service_'):
  ok=True
  for l,r in zip(s['stages'],s['stages'][1:]):
   ok=ok and Q(l['time'][1])==Q(r['time'][0]) and set(l['state'])==set(r['state'])
   for n in l['state']:
    ok=ok and all(Q(x)+Q(d)==Q(y) for k in ('lo','hi') for x,d,y in zip(l['state'][n][k],l['state'][n]['delta'],r['state'][n][k]))
  first,last=s['stages'][0]['state'],s['stages'][-1]['state'];restored=set(first)==set(last) and all(first[n]['lo']==last[n]['lo'] and first[n]['hi']==last[n]['hi'] and last[n]['delta']==['0','0','0'] for n in first)
  result['services'].append({'variant':v,'case':s['case'],'continuous':ok,'restored':restored})
for v in 'AB':
 old_st,new_st=initial(O,v),initial(D,v)
 for p in sorted(T):result['before_after'].append({'variant':v,'pair':list(p),'before_volume_mm3':native(v,p,old_st,Q(0),True),'after_volume_mm3':native(v,p,new_st,Q(0))})
for row in json.loads((R/'verification/r5_layout_output_review/evidence/dynamic_probe.json').read_text()):
 if tuple(sorted(row['pair'])) not in P:continue
 scene=next(s for s in S if s['variant']==row['variant'] and s['case']=='sufficient');stage=next(st for st in scene['stages'] if st['phase']==row['phase']);u=(Q(row['sample_time'])-Q(stage['time'][0]))/(Q(stage['time'][1])-Q(stage['time'][0]));vol=native(row['variant'],tuple(row['pair']),stage['state'],u);assert vol<=1e-5
 historical.append({'original':row,'current_native_volume_mm3':vol})
result['historical_R5_witnesses']=historical;result['secondary_control_counts']=secondary_counts;assert secondary_counts=={'NO_POSITIVE_VOLUME':187}
assert D['config']==O['config'] and all(D['parameters'][ref]==O['parameters'][ref] for ref in O['config'].values())
result['motion_config_unchanged']=True
# Enumerate the 29 expected joint pairs independently of the new run.joint_pairs.
joints=[]
for rail in ('side_rail_L','side_rail_R'):
 joints.extend((('crossbar'+str(i),rail) for i in range(3)));joints.append(('cylinder_seat_bridge',rail))
joints += [('crossbar0','cylinder_mount_rear'),('crossbar2','output_support'),('cylinder_seat_bridge','cylinder_mount_front')]
for side in 'LR':
 joints.append(('cylinder_mount_front','cylinder_seat_'+side))
 for i in range(3):joints.extend([('upper_post_'+side+str(i),'base_'+side),('upper_post_'+side+str(i),'side_rail_'+side)])
joints.extend(('cylinder_barrel',n) for n in ('cylinder_mount_rear','cylinder_mount_front','cylinder_seat_L','cylinder_seat_R'))
def face_area(a,b):
 area=0.
 for f in a.Faces:
  if 'Plane' not in type(f.Surface).__name__:continue
  for g in b.Faces:
   if 'Plane' not in type(g.Surface).__name__:continue
   # Require opposing outward normals and coplanar native faces through distance.
   if f.normalAt(0,0).dot(g.normalAt(0,0))<-0.999999999 and f.distToShape(g)[0]<1e-8:area+=f.common(g).Area
 return area
result['interfaces']=[];result['conditional_graph']={}
for v in 'AB':
 graph=collections.defaultdict(set)
 for a,b in joints:
  sa,sb=objects[v][a].Shape,objects[v][b].Shape;area=face_area(sa,sb);volume=sa.common(sb).Volume
  result['interfaces'].append({'variant':v,'pair':sorted((a,b)),'opposing_planar_face_area_mm2':area,'native_volume_mm3':volume})
  if area>0 and volume<=1e-5:graph[a].add(b);graph[b].add(a)
 if v=='B':
  for a,b in [('end_stop','lock'),('lock','stop_support'),('lock','stop_support_L'),('stop_support','stop_support_bridge'),('stop_support_L','stop_support_bridge'),('stop_support_bridge','side_rail_L'),('stop_support_bridge','side_rail_R')]:
   area=face_area(objects[v][a].Shape,objects[v][b].Shape);assert area>0
   graph[a].add(b);graph[b].add(a)
 todo=['cylinder_barrel'];seen=set()
 while todo:
  n=todo.pop()
  if n not in seen:seen.add(n);todo.extend(graph[n]-seen)
 required={'base_L','base_R','side_rail_L','side_rail_R','cylinder_mount_rear','cylinder_mount_front','output_support'}|({'end_stop'} if v=='B' else set())
 result['conditional_graph'][v]={'connected_to_barrel':sorted(seen),'required_missing':sorted(required-seen),'capacity_fasteners_radial_restraint':'UNKNOWN'}
# Every retained non-CLEAR pair/context/class must survive the finite inventory.
registry=json.loads((out/'inventory/inventory.json').read_text());raw=collections.defaultdict(lambda:{'classes':collections.Counter(),'contexts':set()})
with gzip.open(out/'classifications.jsonl.gz','rt') as f:
 for line in f:
  x=json.loads(line)
  if x['class']=='CLEAR':continue
  key=(x['variant'],tuple(x['pair']));raw[key]['classes'][x['class']]+=1;raw[key]['contexts'].add((x['case'],x['phase']))
rows={(r['variant'],tuple(r['pair'])):r for r in registry['rows']};assert set(raw)==set(rows)
for key,r in rows.items():
 assert raw[key]['classes']==r['classes'] and raw[key]['contexts']=={(c['case'],c['phase']) for c in r['contexts']},key
result['registry_summary']=registry['summary'];result['registry_rows']=len(rows);result['remaining_native']=[]
lookup={(s['variant'],s['case'],st['phase']):st for s in S for st in s['stages']}
for key,r in rows.items():
 if r['classification']!='NATIVE_PENETRATION':continue
 witnesses=[]
 for w in r['native_representatives']:
  st=lookup[(r['variant'],w['case'],w['phase'])];u=(Q(w['time'])-Q(st['time'][0]))/(Q(st['time'][1])-Q(st['time'][0]));vol=native(r['variant'],tuple(r['pair']),st['state'],u)
  witnesses.append({'case':w['case'],'phase':w['phase'],'time':w['time'],'volume_mm3':vol})
 assert any(w['volume_mm3'] is not None and w['volume_mm3']>1e-5 for w in witnesses),key
 assert r['status']=='OPEN' and not r['control_context']
 result['remaining_native'].append({'id':r['id'],'variant':r['variant'],'pair':r['pair'],'witnesses':witnesses,'status':r['status']})
result['independent_all_positive_native_pairs']=list(all_positive_native.values())
result['positive_control_pairs_without_persisted_native_object']=[list(k) for k in sorted(bound_positive_controls)]
result['curved_bound_candidates']=[list(k) for k in sorted(curved_bound_candidates)]
assert set(all_positive_native)=={(r['variant'],*r['pair']) for r in result['remaining_native']},'positive native pair not in the twenty OPEN registry rows'
# Saved positive-face classifications never remove raw contexts or classes.
result['conditional_interfaces_are_initial_only']=True
result['native_unique_common_checks']=len(cache);result['native_dimension_states']=len(dims)
assert not result['coverage_errors'] and not result['positive_changed'] and not result['native_target_positive']
assert all(r['before_volume_mm3']>1e-5 and r['after_volume_mm3']<=1e-5 for r in result['before_after'])
assert all(r['opposing_planar_face_area_mm2']>0 and r['native_volume_mm3']<=1e-5 for r in result['interfaces'])
assert all(not r['required_missing'] for r in result['conditional_graph'].values())
assert len(result['remaining_native'])==20 and all(r['continuous'] and r['restored'] for r in result['services'])
Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+'\n')
for docs_ in (docs,before_docs):
 for d in docs_.values():App.closeDocument(d.Name)
print({k:v for k,v in result.items() if k not in ('target_rows','interfaces','native_adapter','remaining_native','conditional_graph')})
