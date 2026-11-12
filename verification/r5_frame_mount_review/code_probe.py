"""Independent counterexamples for new frame_mount code and current-cycle inputs."""
import copy,gzip,json,random,sys
from fractions import Fraction as F
from pathlib import Path
R=Path(sys.argv[1]).resolve();sys.path.insert(0,str(R/'cad/frame_mount'))
from geometry_evidence import strict_interval
from run import module_service,joint_pairs
from outcomes import assess_scene,evaluate_suite
from verify_cycles import verify_cycles
from layout_common import load
D=load(R/'cad/frame_mount/inputs.assumed.json');S=json.loads(gzip.decompress((R/'cad/build/frame_mount/raw_checked_tool/all_pairs.json.gz').read_bytes()));rows=[]
def body(lo,hi,delta=('0','0','0'),motion='linear'):return dict(lo=list(map(str,lo)),hi=list(map(str,hi)),delta=None if delta is None else list(map(str,delta)),motion=motion)
def ref(a,b):
 if a['motion']!='linear' or b['motion']!='linear' or a['delta'] is None or b['delta'] is None:return 'INDETERMINATE'
 lines=[];knots={F(0),F(1)}
 for i in range(3):
  for c,v in [(F(a['hi'][i])-F(b['lo'][i]),F(a['delta'][i])-F(b['delta'][i])),(F(b['hi'][i])-F(a['lo'][i]),F(b['delta'][i])-F(a['delta'][i]))]:
   lines.append((c,v))
   if v and 0<=-c/v<=1:knots.add(-c/v)
 knots=sorted(knots)
 return 'POSITIVE_BOUND_OVERLAP' if any(all(c+v*t>0 for c,v in lines) for t in knots+[(a+b)/2 for a,b in zip(knots,knots[1:])]) else 'NO_POSITIVE_VOLUME_ON_INTERVAL'
def trial(tag,a,b,want=None):
 want=want or ref(a,b);got=strict_interval(a,b)['status'];rows.append({'id':tag,'expected':want,'actual':got,'pass':got==want})
a=body((0,0,0),(1,1,1),(4,0,0));b=body((2,0,0),(3,1,1));trial('midstroke_only',a,b,'POSITIVE_BOUND_OVERLAP')
trial('return_midstroke_only',body((4,0,0),(5,1,1),(-4,0,0)),b,'POSITIVE_BOUND_OVERLAP')
for tag,lo,hi in [('face',(1,0,0),(2,1,1)),('edge',(1,1,0),(2,2,1)),('point',(1,1,1),(2,2,2))]:trial(tag,body((0,0,0),(1,1,1)),body(lo,hi),'NO_POSITIVE_VOLUME_ON_INTERVAL')
trial('small_positive',body((0,0,0),(1,1,1)),body((F(1)-F(1,10**30),0,0),(2,1,1)),'POSITIVE_BOUND_OVERLAP')
trial('touch_only_at_end',body((0,0,0),(1,1,1),(1,0,0)),body((2,0,0),(3,1,1)),'NO_POSITIVE_VOLUME_ON_INTERVAL')
trial('start_penetration_then_clear',body((0,0,0),(1,1,1),(-3,0,0)),body((F(1,2),0,0),(2,1,1)),'POSITIVE_BOUND_OVERLAP')
for mode in ('rotation','spline',None):trial('unsupported_'+str(mode),body((0,0,0),(1,1,1),motion=mode),b,'INDETERMINATE')
trial('unknown_delta',body((0,0,0),(1,1,1),None),b,'INDETERMINATE')
rng=random.Random(5198)
for i in range(500):
 def rb():
  lo=[F(rng.randrange(-8,9),4) for _ in range(3)];hi=[x+F(rng.randrange(1,9),4) for x in lo];d=[F(rng.randrange(-8,9),4) for _ in range(3)];return body(lo,hi,d)
 trial('relative_3d_'+str(i),rb(),rb())
suite=evaluate_suite(S,D);rows.append({'id':'actual_eight_cycles','pass':suite['status']=='PASS' and len(verify_cycles(S,D))==8 and sum(s['limited_cycle_success'] for s in suite['scene_results'])==2})
for v in 'AB':
 service=module_service(D,v);stages=service['stages'];ids=set(stages[0]['state']);moving=[]
 for st in stages:
  movers={n for n,b in st['state'].items() if b['delta']!=['0','0','0']};moving.append(sorted(movers));assert set(st['state'])==ids
 rows.append({'id':v+'_module_service','actual_movers':moving,'pass':moving==[[],['cylinder_barrel','rod'],['cylinder_barrel','rod'],[]] and service['continuity_status']=='CONTINUOUS' and service['positions_restored']})
 base=next(s for s in S if s['variant']==v and s['case']=='sufficient')
 for tag in ('required_link','path_transition','continuity_status','lifecycle','path_ready','compound'):
  s=copy.deepcopy(base)
  changes={'required_link':'LINK_ABSENT','path_transition':'BLOCKED','continuity_status':'INDETERMINATE','lifecycle':[],'path_ready':'NOT_CONFIRMED'}
  for k,value in changes.items():
   if k==tag or tag=='compound':s[k]=value
  r=assess_scene(s,D);payload=[s if x['variant']==v and x['case']=='sufficient' else x for x in S];rejected=False
  try:verify_cycles(payload,D)
  except (AssertionError,KeyError,ValueError,TypeError):rejected=True
  rows.append({'id':v+'_lost_'+tag,'pass':not r['matches_expectation'] and not r['limited_cycle_success'] and rejected})
j=joint_pairs();rows.append({'id':'joint_set_unique','pass':len(j)==len({tuple(x['pair']) for x in j})==29})
r={'cases':rows,'count':len(rows),'passed':sum(bool(x['pass']) for x in rows),'failed':[x['id'] for x in rows if not x['pass']]};Path(sys.argv[2]).write_text(json.dumps(r,indent=2)+'\n');print(r['count'],r['passed'],r['failed']);sys.exit(bool(r['failed']))
