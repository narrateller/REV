"""Independent compound fixtures through calculation -> report -> verifier ->
explicit reanalysis. All mutations and restorations are harness-only in COPY.
No import of author's service_fixtures. Outputs must be outside COPY.
"""
import copy,gzip,hashlib,json,os,subprocess,sys
from fractions import Fraction as F
from pathlib import Path
R=Path(sys.argv[1]).resolve();dest=Path(sys.argv[2]);assert not dest.is_relative_to(R)
sys.path.insert(0,str(R/'cad/feed_power'));from service_semantics import Evaluator,evaluate_scene,evaluate_services
from common import checked,load,INPUT,OUT,config
D=load(INPUT);S=json.loads(gzip.decompress((OUT/'service_scenes.json.gz').read_bytes()));E=json.loads(gzip.decompress((OUT/'work_and_extra.json.gz').read_bytes()));evaluator=Evaluator(D,OUT)
files=('service_scenes.json.gz','work_and_extra.json.gz','publication_manifest.json','service_report.json','assessment.md');original={n:((OUT/n).read_bytes(),(OUT/n).stat()) for n in files};records=[];results=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def snapshot():return {str(p.relative_to(R)):(sha(p),p.stat().st_size,p.stat().st_mtime_ns) for p in R.rglob('*') if p.is_file() and not {'.git','.venv','__pycache__'}&set(p.parts)}
def persist():dest.write_text(json.dumps({'cases':results,'commands':records},indent=2)+'\n')
def restore():
 for n,(data,st) in original.items():(OUT/n).write_bytes(data);os.utime(OUT/n,ns=(st.st_atime_ns,st.st_mtime_ns))
def seal_fixture():
 m=json.loads(original['publication_manifest.json'][0])
 for n in files:
  if n!='publication_manifest.json':m['sha256']['cad/build/feed_power/'+n]=sha(OUT/n)
 (OUT/'publication_manifest.json').write_text(json.dumps(m,indent=2)+'\n')
def command(tag,cmd,expected=1,readonly=False):
 before=snapshot();p=subprocess.run(cmd,cwd=R,capture_output=True,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'});after=snapshot();delta=[n for n in before.keys()|after.keys() if before.get(n)!=after.get(n)]
 rec={'label':tag,'command':cmd,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'read_only_required':readonly,'file_changes':delta};records.append(rec);persist();print(tag,p.returncode,flush=True)
 assert p.returncode==expected,(tag,p.stdout,p.stderr)
 if readonly:assert not delta,(tag,delta)
 return p

def scene(v,name):return copy.deepcopy(next(s for s in S if s['variant']==v and s['case']=='service_fp_'+name))
def refresh(s):
 for st in s['stages']:
  # Raw evidence comes from the frozen public API, not the code under recheck.
  st['pairs']=checked.matrix(st['state'],st['time'],s['variant']);st['counts']=checked.summarize(st['pairs'])
 s['continuity']=checked.assess_continuity(s['stages'],[]);s['continuity_status']=checked.continuity_status(s['continuity']);end=checked.advance(s['stages'][-1]['state']);start=s['stages'][0]['state'];s['positions_restored']=set(end)==set(start) and all(end[n]['lo']==start[n]['lo'] and end[n]['hi']==start[n]['hi'] for n in start);return s

def replan(base,moves):
 s=copy.deepcopy(base);current=copy.deepcopy(s['stages'][0]['state'])
 for i,st in enumerate(s['stages']):
  state=copy.deepcopy(current)
  for body in state.values():body['delta']=['0','0','0']
  if 0<i<len(s['stages'])-1:
   for n,d in moves[i-1]:state[n]['delta']=list(map(str,d))
  st['state']=state;current=checked.advance(state)
 return refresh(s)

def target(sem,mutant):return next(r for r in sem['service_scenes'] if (r['variant'],r['case'])==(mutant['variant'],mutant['case']))
def assert_outcome(row,want,collision=None):
 assert row['geometric_path_outcome']==row['overall_service_outcome']==want,row
 assert not row['limited_geometry_success'] and not row['matches_test_expectation'] and row['physical_feasibility']=='INDETERMINATE'
 if collision is True:assert row['proven_collisions']
 if collision is False:assert not row['proven_collisions']
 if want=='INDETERMINATE':assert row['unknown_mandatory_conditions']

def run_case(label,mutant,want,collision=None):
 restore();fresh=evaluate_scene(mutant,D,evaluator);assert_outcome(fresh,want,collision)
 for n,source in [('service_scenes.json.gz',S),('work_and_extra.json.gz',E)]:
  payload=[mutant if (s['variant'],s['case'])==(mutant['variant'],mutant['case']) else s for s in source];(OUT/n).write_bytes(gzip.compress(json.dumps(payload,sort_keys=True,separators=(',',':')).encode(),mtime=0))
 seal_fixture()
 p=command(label+'/calculation',['/usr/bin/python3','-B','cad/feed_power/service_semantics.py'],readonly=True);sem=json.loads(p.stdout);assert sem['calculation_execution']=='COMPLETED' and sem['test_evaluation']=='FAIL';assert_outcome(target(sem,mutant),want,collision)
 p=command(label+'/report',['/usr/bin/python3','-B','cad/feed_power/present.py','--report-only']);report=json.loads((OUT/'service_report.json').read_text());assert_outcome(target(report,mutant),want,collision)
 assert f"| {mutant['variant']} | {mutant['case']} | {want} |" in (OUT/'assessment.md').read_text()
 # Refresh explicit report hashes so verifier reaches semantics, not hash guard.
 seal_fixture();p=command(label+'/verifier',['/usr/bin/python3','-B','cad/feed_power/verify_output.py'],readonly=True);v=json.loads(p.stdout);assert v['status']=='FAIL' and v['execution']=={'status':'COMPLETED','exit_code':1};assert_outcome(target(v['service_semantics'],mutant),want,collision)
 p=command(label+'/reanalysis',['/usr/bin/python3','-B','cad/feed_power/generate.py','--reanalyze'],readonly=True);g=json.loads(p.stderr);assert g['execution']=={'status':'COMPLETED','exit_code':1} and g['test_evaluation']=='FAIL';assert_outcome(target(g['service_semantics'],mutant),want,collision)
 results.append({'case':label,'expected_path':want,'fresh_calculation_and_aggregation':fresh,'report_path':target(report,mutant)['geometric_path_outcome'],'verifier_path':target(v['service_semantics'],mutant)['geometric_path_outcome'],'reanalysis_path':target(g['service_semantics'],mutant)['geometric_path_outcome'],'all_cli_exits':[1,1,1,1],'negative_test_is_path_success':False});persist();restore()

lift=config(D,'service_lift');z=F(0)
# Independent variants of the original proven collision; motions use frozen API.
short=replan(scene('B','doser_retract_lift'),[[('doser_slide',(z,z,z))],[('doser_slide',(z,z,lift))],[('doser_slide',(z,z,-lift))],[('doser_slide',(z,z,z))]])
s=copy.deepcopy(short);s['stages'][2]['state']['pump_motor']['motion']='rotation';run_case('collision_plus_unrelated_rotation',refresh(s),'BLOCKED',True)
s=copy.deepcopy(short);s['stages'][2]['state']['pump_motor']['delta']=None;run_case('collision_plus_unknown_delta',refresh(s),'BLOCKED',True)
s=scene('B','motor');s['stages'][1]['state']['pump_motor']['motion']='rotation';s=refresh(s);s['stages'][1]['pairs'].pop();run_case('unsupported_rotation_plus_missing_pair',s,'INDETERMINATE')
s=scene('B','doser_retract_lift');duration=config(D,'phase_duration');s['stages'][2]['time']=[str(F(t)+duration) for t in s['stages'][2]['time']];run_case('clear_intervals_but_time_gap',refresh(s),'BLOCKED',False)
s=scene('B','doser_retract_lift')
for k in ('lo','hi'):s['stages'][-1]['state']['doser_slide'][k][1]=str(F(s['stages'][-1]['state']['doser_slide'][k][1])+F(1,1000))
run_case('clear_intervals_but_nominal_return_jump',refresh(s),'BLOCKED',False)
s=scene('B','motor');s['stages'].pop();run_case('missing_final_phase',refresh(s),'INDETERMINATE')
s=scene('B','motor')
for st in s['stages']:del st['state']['control_cabinet']
run_case('missing_required_registry_body',refresh(s),'INDETERMINATE')
s=copy.deepcopy(short)
for st in s['stages']:st['state']['doser_slide']['group']='routes'
s['stages'][2]['state']['pump_motor']['motion']='rotation';run_case('forged_routes_metadata_plus_collision_and_unknown',refresh(s),'BLOCKED',True)
restore()
# Positive baseline demonstrates negative expectation != successful service.
baseline=evaluate_services(D,S,evaluator);assert baseline['test_evaluation']=='PASS' and baseline['geometric_path_counts']=={'CONFIRMED_NO_POSITIVE_VOLUME':20,'BLOCKED':2};assert baseline['overall_service_counts']=={'INDETERMINATE':20,'BLOCKED':2}
for row in baseline['service_scenes']:
 if row['case']=='service_doser_slide':assert row['matches_test_expectation'] and not row['limited_geometry_success'] and row['overall_service_outcome']=='BLOCKED' and {tuple(x['pair']) for x in row['proven_collisions']}=={tuple(sorted(('doser_slide',n))) for n in ('hopper_R','hopper_floor_right','receiving_rim_right')}
results.append({'case':'restored_baseline_aggregation','test_evaluation':baseline['test_evaluation'],'geometric_counts':baseline['geometric_path_counts'],'overall_counts':baseline['overall_service_counts'],'expected_negative_not_success':True});persist();evaluator.close();print('PASS: independent compound chain and restored baseline')
