import sys,json,tempfile,shutil
from pathlib import Path
sys.path.insert(0,sys.argv[1]+'/cad/layout')
from check_layout import assess_continuity,continuity_status,check_cad_adapter,load

def box(x):return {'lo':[str(x),'0','0'],'hi':[str(x+1),'1','1'],'delta':['0','0','0'],'motion':'linear','exact_box':True}
results=[]
stages=[{'phase':'EJECT','time':['0','1'],'state':{'product_B':box(0)}},{'phase':'RESET','time':['1','2'],'state':{}}]
event={'type':'REMOVE','id':'product_B','time':'1','final_rear':'0','exit_boundary':'2'}
r=assess_continuity(stages,[event]);results.append({'id':'PREMATURE_REMOVE','expected':'not CONTINUOUS: rear 0 is before exit 2','actual':r,'status':continuity_status(r)});assert continuity_status(r)=='CONTINUOUS'
stages=[{'phase':'EJECT','time':['0','1'],'state':{'product_B':box(0)}},{'phase':'RESET','time':['1','2'],'state':{'product_B':box(0)}}]
r=assess_continuity(stages,[{'type':'CREATE','id':'ghost','time':'1'}]);results.append({'id':'UNSUPPORTED_CREATE_IGNORED','expected':'UNKNOWN/INVALID rather than CONTINUOUS','actual':r,'status':continuity_status(r)});assert continuity_status(r)=='CONTINUOUS'
created=[{'phase':'before','time':['0','1'],'state':{}},{'phase':'after','time':['1','2'],'state':{'fragment':box(0)}}]
r=assess_continuity(created,[{'type':'CREATE','id':'fragment','time':'1'}]);results.append({'id':'UNSUPPORTED_CREATE_BLOCKED_NOT_INDETERMINATE','expected':'explicit unsupported INDETERMINATE evidence','actual':r,'status':continuity_status(r)})
p=Path(sys.argv[1]);ip=p/'cad/layout/conditional_inputs.assumed.json';data=load(ip)
with tempfile.TemporaryDirectory() as t:
 for v in 'AB':
  (Path(t)/v).mkdir();shutil.copyfile(p/f'cad/build/research_layout/{v}/manifest.json',Path(t)/v/'manifest.json')
 r=check_cad_adapter(data,t,ip);results.append({'id':'NO_CAD_FILES_STILL_ADAPTER_PASS','expected':'CAD existence/read/shape check required for claim actual CAD match','actual':r});assert all(x['nominal_bounds_match']=='PASS' for x in r.values())
print(json.dumps(results,indent=2));Path(sys.argv[2]).write_text(json.dumps(results,indent=2)+'\n')
