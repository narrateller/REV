"""Exercise verifier CLI with complete early inputs; require semantic rejection.
ROOT is copied implementation, NEGATIVE is completed unlinked build output.
"""
import copy,gzip,hashlib,json,subprocess,sys,tempfile
from pathlib import Path
root=Path(sys.argv[1]).resolve();negative=Path(sys.argv[2]).resolve();out=Path(sys.argv[3]);positive=root/'cad/build/layout_correction';records=[]
def invoke(tag,folder,expected_reason):
 p=subprocess.run(['/usr/bin/python3','cad/layout_correction/verify_output.py','--out',str(folder)],cwd=root,text=True,capture_output=True)
 report=json.loads((folder/'verification.json').read_text());reason=report.get('reason','')
 records.append({'id':tag,'command':p.args,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'report':report,'expected_reason':expected_reason,'pass':p.returncode==1 and expected_reason in reason and report.get('test_evaluation',{}).get('status')=='FAIL'})
invoke('fresh_unlinked',negative,'assessment.json')
base=json.loads((positive/'run.json').read_text());scenes=json.loads(gzip.decompress((positive/'raw_checked_tool/all_pairs.json.gz').read_bytes()));neg_scenes=json.loads(gzip.decompress((negative/'raw_checked_tool/all_pairs.json.gz').read_bytes()))
with tempfile.TemporaryDirectory(prefix='r5-669-verifier-fixtures-') as t:
 for tag,expected in [('unlinked_with_assessment','strict test evaluation failed'),('forged_success_over_unlinked','mandatory outcome'),('forged_report_and_raw_link','actual required link'),('lost_transition','mandatory outcome'),('lost_continuity','mandatory outcome'),('lost_lifecycle',''),('lost_READY','phase sequence'),('compound_lifecycle_return_unknown','mandatory outcome')]:
  folder=Path(t)/tag;(folder/'raw_checked_tool').mkdir(parents=True)
  (folder/'assessment.json').write_bytes((positive/'assessment.json').read_bytes());run=copy.deepcopy(base);s=copy.deepcopy(scenes)
  if tag=='unlinked_with_assessment':run=json.loads((negative/'run.json').read_text());s=neg_scenes
  if tag in ('forged_success_over_unlinked','forged_report_and_raw_link'):
   s=copy.deepcopy(neg_scenes)
   if tag=='forged_report_and_raw_link':
    # Preserve the failed physical link but forge every successful summary label.
    for i,scene in enumerate(s):
     if scene['case']=='sufficient':
      for k in ('geometry','path_collision','required_link','path_transition','continuity_status','path_ready'):scene[k]=scenes[i][k]
      # Supply missing return stages so that actual-link recomputation is reached.
      scene['stages']=scene['stages']+copy.deepcopy(scenes[i]['stages'][len(scene['stages']):])
  if tag.startswith('lost_') or tag=='compound_lifecycle_return_unknown':
   for scene in s:
    if scene['case']!='sufficient':continue
    if tag=='lost_transition':scene['path_transition']='BLOCKED'
    if tag=='lost_continuity':scene['continuity_status']='INDETERMINATE'
    if tag=='lost_lifecycle':scene['lifecycle']=[]
    if tag=='lost_READY':scene['stages'].pop()
    if tag=='compound_lifecycle_return_unknown':scene['lifecycle']=[];scene['stages'].pop();scene['required_link']='LINK_INDETERMINATE'
  raw=gzip.compress(json.dumps(s).encode());(folder/'raw_checked_tool/all_pairs.json.gz').write_bytes(raw)
  if 'artifacts' in run:run['artifacts']['raw_checked_tool/all_pairs.json.gz']=hashlib.sha256(raw).hexdigest()
  (folder/'run.json').write_text(json.dumps(run))
  invoke(tag,folder,expected)
# An empty assertion reason (lifecycle) is acceptable only when no late missing-file
# fallback occurred; capture the stderr, which is "VERIFICATION FAILED: " here.
for r in records:
 if r['id']=='lost_lifecycle':r['pass']=r['pass'] and r['report']['reason']=='' and r['stderr'].strip()=='VERIFICATION FAILED:'
result={'count':len(records),'passed':sum(r['pass'] for r in records),'cases':records};out.write_text(json.dumps(result,indent=2)+'\n');print(result['count'],result['passed']);sys.exit(result['passed']!=result['count'])
