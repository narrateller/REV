import sys,copy,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2] / 'models/kinematic_press'))
import linked
original=linked.assess_continuity
for v in 'AB':
 for kind in ('position','time','lifecycle','unknown'):
  def altered(stages,lifecycle,kind=kind):
   s=copy.deepcopy(stages); l=copy.deepcopy(lifecycle)
   if len(s)<2:return original(s,l)
   if kind=='position':
    b=s[1]['bodies']['gate']; b['min'][0]=str(int(b['min'][0])+1); b['max'][0]=str(int(b['max'][0])+1)
   if kind=='time':s[1]['time'][0]+=1
   if kind=='unknown':s[0]['bodies']['gate']['delta']=None
   if kind=='lifecycle':
    del s[1]['bodies']['gate']
   return original(s,l)
  linked.assess_continuity=altered
  r=linked.run(v,'sufficient'); want='INDETERMINATE' if kind=='unknown' else 'BLOCKED'
  assert (r['transition'],r['ready']['status'])==(want,want),(v,kind,r['transition'],r['ready']['status'])
  print(v,kind,want,'PASS')
linked.assess_continuity=original
for name in ('report.json','linked_report.json'):
 saved=json.loads(__import__('subprocess').check_output(['git','show','debfd085:models/kinematic_press/results/'+name]))
 p='/tmp/r5-05-basic/report.json' if name=='report.json' else 'models/kinematic_press/results/linked_report.json'
 fresh=json.load(open(p)); print(name,'same_except_python', {k:v for k,v in saved.items() if k!='python'}=={k:v for k,v in fresh.items() if k!='python'})
 print('hashes',sum(hashlib.sha256(open(p,'rb').read()).hexdigest()==h for p,h in fresh['hashes'].items()),'/',len(fresh['hashes']))
