import sys,json,copy
from pathlib import Path
from fractions import Fraction as F
sys.path.insert(0,sys.argv[1]+'/cad/layout_correction');import assess
from layout_common import load,selected
out=[]
def box(x,motion='linear'):return {'lo':[str(x),'0','0'],'hi':[str(F(x)+1),'1','1'],'delta':['0','0','0'],'motion':motion,'exact_box':True,'group':'test'}
state={'moving':box(0,'rotation'),'wall':box(4)}
raw=assess.checked.evaluate_pair(state['moving'],state['wall'],'moving','wall',['0','1'],'A');c=assess.classify(raw,state,['0','1'],'A')
assert raw['status']=='INDETERMINATE' and c['class']=='CLEAR'
out.append({'case':'unsupported_motion_becomes_clear','expected':'INDETERMINATE; linear partition not applicable','raw':raw,'classified':c})
data=load(Path(sys.argv[1])/'cad/layout_correction/inputs.assumed.json')
for v in 'AB':
 d=copy.deepcopy(data);comp=next(c for c in selected(d,v) if c['id']=='product_'+v);ref=comp['position'][0];d['parameters'][ref]['value']=str(F(d['parameters'][ref]['value'])+F('1/100'))
 result=assess.checked.scenario(d,v,'sufficient');predicate=(result['geometry'],result['path_collision'])==('GEOMETRY_SUFFICIENT','NO_COLLISION')
 assert predicate and result['required_link']=='LINK_ABSENT' and result['path_transition']=='BLOCKED' and result['path_ready']=='NOT_CONFIRMED'
 out.append({'case':'sufficient_oracle_ignores_link_'+v,'expected':'reject sufficient outcome without confirmed link/return','product_offset_m':'1/100','run_revision_outcome_predicate':predicate,'result':{k:result[k] for k in ('geometry','path_collision','required_link','path_transition','path_ready','continuity_status')},'phases':[s['phase'] for s in result['stages']]})
Path(sys.argv[2]).write_text(json.dumps(out,indent=2)+'\n');print([(r['case'],r.get('result',r.get('classified'))) for r in out])
