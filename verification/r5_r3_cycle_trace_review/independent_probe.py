"""Independent checks of committed coordinates/parameters; NOT native geometry.

No author collect(), CAD generation, BRep, model solver or physical trial is used.
"""
import gzip,hashlib,json,math,subprocess,sys
from fractions import Fraction as F
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
from repo_support import flatten,engineering_sha
CAD='3591a5f92f78b1edea07d3fc5354fd0a99090798'
CALC='c115f75fd900525d9ddc89d85e097ac5a0f00bc1'
HERE=ROOT/'verification/r3_cycle_trace'
hashes={}
def load(path,compressed=False):
 raw=subprocess.check_output(['git','show',CAD+':'+path],cwd=ROOT);hashes[path]=hashlib.sha256(raw).hexdigest()
 return json.loads(gzip.decompress(raw) if compressed else raw)
def end_box(body):
 return {k:[F(v)+F(d) for v,d in zip(body[k],body['delta'])] for k in ('lo','hi')}
def box(body):return {k:list(map(F,body[k])) for k in ('lo','hi')}
saved=json.loads((HERE/'cad_evidence.json').read_text());records={}
for variant in 'AB':
 folder='cad/build/calculated_layout/'+variant
 scenes=load(folder+'/scenes.json.gz',True);s=next(x for x in scenes if x['case']=='sufficient')
 result=load(folder+'/results.json');nominal=next(x for x in result['scene_results'] if x['case']=='sufficient')
 inp=load('cad/calculated_layout/inputs.BASE_'+variant+'.json')
 phases={x['phase']:x for x in s['stages']};continuity_checks=0
 for a,b in zip(s['stages'],s['stages'][1:]):
  assert F(a['time'][1])==F(b['time'][0])
  for name in set(a['state'])&set(b['state']):
   assert end_box(a['state'][name])==box(b['state'][name]),(variant,a['phase'],b['phase'],name)
   continuity_checks+=1
 for phase,st in phases.items():
  old=saved['variants'][variant]['phases'][phase]
  assert old['time']==st['time'] and old['permission']==st['permission']
  for name,b in old['bodies'].items():assert b=={k:st['state'][name].get(k) for k in b},(phase,name)
 product='product_'+variant;ready=phases[variant+'-READY']['state'][product]
 dimensions=[F(b)-F(a) for a,b in zip(ready['lo'],ready['hi'])]
 assert dimensions==[F('0.11'),F('0.15'),F('0.06')]
 assert s['lifecycle']==[] and not s['product_removed']
 eject=phases[variant+'-EJECT']['state'][product];rear=end_box(eject)['lo'][0]
 assert rear==F(s['product_rear_after_eject'])
 target=F(inp['parameters'][inp['config']['exit_'+variant]]['value'])
 assert target==F(s['actual_CAD_exit'])
 nominal_plane=F(inp['exact_geometry']['CHAMBER_LENGTH'])+F('0.03')
 assert nominal_plane==F(s['r3_nominal_exit'])
 assert rear>=nominal_plane and rear<target and nominal['actual_output_geometry']=='SHORT_STROKE'
 assert s['READY']=='NOT_CONFIRMED' and s['nominal_return']=='RESTORED_TOOLS_ONLY'
 assert s['stages'][-1]['state'][product]['lo']==[str(x) for x in end_box(eject)['lo']]
 before=F(s['fixed_budget_interval'][0])-F(s['stages'][0]['time'][0])
 after=F(s['full_diagnostic_duration'])-F(s['fixed_budget_interval'][1])
 assert before==3 and after==(2 if variant=='A' else 4)
 assert abs(F(s['fixed_budget_duration'])-F(s['registered_fixed_budget_cycle']))<F('1e-12')
 rod=phases[variant+'-READY']['state']['rod'];rod_d=F(rod['hi'][2])-F(rod['lo'][2])
 assert rod_d>F('0.06')
 gaps=[]
 if variant=='A':
  for clamp,channel in (('clamp_L','channel_left'),('clamp_R','channel_right')):
   one=box(phases['A-READY']['state'][clamp]);two=box(phases['A-READY']['state'][channel])
   separation=[max(F(0),one['lo'][i]-two['hi'][i],two['lo'][i]-one['hi'][i]) for i in range(3)]
   distance=math.sqrt(float(sum(x*x for x in separation)));assert math.isclose(distance,.15,abs_tol=1e-12)
   assert all(not any(F(x) for x in st['state'][clamp]['delta']) for st in s['stages'])
   gaps.append({'pair':[clamp,channel],'declared_bounds_gap_m':distance,'working_motion_present':False,'native_verification':'NOT_RUN'})
 extra={}
 if variant=='B':
  assert s['B_open_permission']=='INDETERMINATE'
  assert all(not any(F(x) for x in b['delta']) for b in phases['B-UNLOAD']['state'].values())
  st=phases['B-RESET-STOP'];stop=st['state']['end_stop'];p=st['state'][product]
  endpoint=end_box(stop);fixed=box(p)
  overlap=[min(endpoint['hi'][i],fixed['hi'][i])-max(endpoint['lo'][i],fixed['lo'][i]) for i in range(3)]
  assert all(x>0 for x in overlap)
  assert stop['exact_box'] and p['exact_box']
  first_touch=(F(stop['lo'][1])-F(p['hi'][1]))/(-F(stop['delta'][1]));assert first_touch==F('11/20')
  extra={'reset_declared_box_overlap_m':list(map(str,overlap)),'reset_declared_box_overlap_volume_m3':str(math.prod(overlap)),
         'reset_first_touch_fraction_of_interval':str(first_touch),'interpretation':'Analytical contradiction of declared exact boxes; actual FCStd/STEP/BRep consistency and all-time native collision NOT_RUN.'}
 records[variant]={'CAD_commit':CAD,'scenes_count':len(scenes),'phases':len(phases),'continuous_body_boundary_checks':continuity_checks,
  'preformed_product_dimensions_m':list(map(str,dimensions)),'material_transformation_events':s['lifecycle'],
  'rear_after_eject_m':str(rear),'simplified_R3_exit_m':str(nominal_plane),'R3_plane_margin_m':str(rear-nominal_plane),
  'declared_CAD_exit_m':str(target),'deficit_to_declared_exit_m':str(target-rear),'reported_output':nominal['actual_output_geometry'],
  'tool_return':s['nominal_return'],'READY':s['READY'],'registered_axis_budget_s':s['registered_fixed_budget_cycle'],
  'full_diagnostic_duration_s':s['full_diagnostic_duration'],'outside_axis_interval_before_s':str(before),'outside_axis_interval_after_s':str(after),
  'rod_envelope_diameter_m':str(rod_d),'selected_chamber_height_m':'3/50','rod_native_collision_independent':'NOT_RUN',
  'interfaces':gaps,'author_positive_pair_records':len(nominal['proven_positive_pairs']),'author_native_witness_truth_independent':'NOT_RUN',**extra}

params=flatten(yaml.safe_load(subprocess.check_output(['git','show',CALC+':params/registry.yaml'],cwd=ROOT)))
rows=json.loads((HERE/'cycle_table.json').read_text());chains=[];refs=set();coverage=set()
for row in rows:
 for p in row['parameters']:
  e=params[p['id']];assert p['revision']==e['revision'] and p['value']==e['value'] and p['unit']==e['unit'] and p['engineering_sha256']==engineering_sha(e)
  refs.add(p['id'])
 assert row['cad']['commit']==CAD
 assert row['hypothesis_status']=='ASSUMED_FUNCTIONAL_ONLY_NOT_APPROVED'
 coverage.add((row['variant'],row['stage']))
 chains.append({'id':row['id'],'variant':row['variant'],'stage':row['stage'],'source_claims':row['sources'],
                'parameter_refs_checked':len(row['parameters']),'CAD_phases':row['cad']['phases'],'source_status':row['status'],
                'independent_conclusion':'Documentary conditional chain; not proof of physical transition or native CAD defect.'})
assert len(rows)==20 and all((v,s) in coverage for v in 'AB' for s in ('load','isolate','press','hold_unload','eject','return','ready'))
print(json.dumps({'scope':'DOCUMENTARY_AND_DECLARED_COORDINATES_ONLY','CAD_review':'NOT_AVAILABLE per user instruction',
 'native_replay':'NOT_RUN','CAD_input_blob_sha256':hashes,'variants':records,'chains':chains,'distinct_calculation_parameters_checked':len(refs),
 'mandatory_variant_stage_cells':14},ensure_ascii=False,indent=2))
