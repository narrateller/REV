"""Independent original R5 replay plus full calculation/report/generator/CLI faults.
All mutations/restorations occur in one disposable local materialized checkout.
"""
import os,shutil,subprocess,tempfile,json,hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];DEST=Path(__file__).parent/'after';DEST.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'cad/feed_power'));from service_fixtures import *

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def snap(root):return {p.relative_to(root).as_posix():(sha(p),p.stat().st_mtime_ns,p.stat().st_size) for folder in ('cad','verification','params','models','drives') for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts}

def main():
 records=[];cases=[];result={'status':'RUNNING','scope':'R4 regression, independent R5 RECHECK NOT_RUN'}
 def run(root,label,cmd,readonly=False):
  before=snap(root) if readonly else None;p=subprocess.run(cmd,cwd=root,text=True,capture_output=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
  if readonly:assert before==snap(root),(label,'command wrote saved data')
  records.append({'label':label,'command':cmd,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr});(DEST/'commands.json').write_text(json.dumps(records,indent=2)+'\n');print(label,p.returncode,flush=True);return p
 try:
  with tempfile.TemporaryDirectory(prefix='rev-fp-recheck-') as temp:
   root=Path(temp)/'REV';subprocess.run(['git','clone','--shared','--no-checkout',str(ROOT),str(root)],check=True,capture_output=True);subprocess.run(['git','checkout','HEAD'],cwd=root,env={**os.environ,'GIT_LFS_SKIP_SMUDGE':'1'},check=True,capture_output=True);subprocess.run(['git','lfs','install','--local'],cwd=root,check=True,capture_output=True)
   for name in subprocess.check_output(['git','lfs','ls-files','-n'],cwd=ROOT,text=True).splitlines():shutil.copy2(ROOT/name,root/name)
   for folder in ('cad/feed_power','cad/build/feed_power','verification/r4_feed_power'):shutil.copytree(ROOT/folder,root/folder,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
   original=run(root,'original_R5_probe_after_fix',['/usr/bin/python3','-B',str(ROOT/'verification/r5_feed_power_review/service_counterexamples.py'),str(root),str(DEST/'original_R5_after.json')]);assert original.returncode==0
   r5=json.loads((DEST/'original_R5_after.json').read_text());assert len(r5['cases'])==5
   for r in r5['cases']:
    assert r['actual_verifier_exit']==1 and not r['verifier_writes']
    case_name='service_fp_powerpack_module' if 'powerpack' in r['id'] else 'service_fp_motor' if 'unsupported' in r['id'] else 'service_fp_doser_retract_lift';v=r['id'][0]
    target=next(x for x in r['stdout']['service_semantics']['service_scenes'] if x['variant']==v and x['case']==case_name);want='INDETERMINATE' if 'unsupported' in r['id'] else 'BLOCKED'
    assert target['geometric_path_outcome']==want and not target['limited_geometry_success'] and target['physical_feasibility']=='INDETERMINATE'
   data=load(INPUT);services=read_packed(OUT/'service_scenes.json.gz');extra=read_packed(OUT/'work_and_extra.json.gz');evaluator=Evaluator(data);mutants=counterexamples(data,services,evaluator)
   files=['service_scenes.json.gz','work_and_extra.json.gz','publication_manifest.json','service_report.json','assessment.md'];originals={name:((root/'cad/build/feed_power'/name).read_bytes(),(root/'cad/build/feed_power'/name).stat()) for name in files}
   for index,(label,mutated,want) in enumerate(mutants):
    output=root/'cad/build/feed_power'
    for filename,source in [('service_scenes.json.gz',services),('work_and_extra.json.gz',extra)]:
     current=[mutated if (s['variant'],s['case'])==(mutated['variant'],mutated['case']) else s for s in source];packed(output/filename,current)
    manifest=json.loads(originals['publication_manifest.json'][0])
    for name in ('service_scenes.json.gz','work_and_extra.json.gz'):manifest['sha256']['cad/build/feed_power/'+name]=sha(output/name)
    (output/'publication_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    actual=evaluate_scene(mutated,data,evaluator);assert actual['geometric_path_outcome']==want and not actual['matches_test_expectation'];entry={'id':label,'expected':want,'calculation_and_aggregation':actual}
    # First five verifier CLI cases were already run by the unchanged independent
    # R5 probe. Exercise additional compound verifier cases here.
    if index>=5:
     p=run(root,label+'-verifier',['/usr/bin/python3','-B','cad/feed_power/verify_output.py'],True);assert p.returncode==1;entry['verifier_stdout']=json.loads(p.stdout)
    if index<5 or index==5:
     p=run(root,label+'-calculation-CLI',['/usr/bin/python3','-B','cad/feed_power/service_semantics.py'],True);assert p.returncode==1;calc=json.loads(p.stdout);entry['calculation_CLI']=calc['test_evaluation'];assert calc['test_evaluation']=='FAIL'
     p=run(root,label+'-report-CLI',['/usr/bin/python3','-B','cad/feed_power/present.py','--report-only']);assert p.returncode==1
     report=json.loads((output/'service_report.json').read_text());target=next(x for x in report['service_scenes'] if x['variant']==mutated['variant'] and x['case']==mutated['case']);assert target['geometric_path_outcome']==want
     assert '| '+mutated['variant']+' | '+mutated['case']+' | '+want+' |' in (output/'assessment.md').read_text();entry['report_path_outcome']=target['geometric_path_outcome']
     before=snap(root);p=run(root,label+'-generator-CLI',['/usr/bin/python3','-B','cad/feed_power/generate.py','--reanalyze']);assert p.returncode==1 and before==snap(root),'failed generation repaired/resealed a bad service path';g=json.loads(p.stderr);assert g['execution']['status']=='COMPLETED' and g['test_evaluation']=='FAIL';entry['generation_validation']='FAIL_WITHOUT_REPAIR'
    cases.append(entry)
    for name,(content,stat) in originals.items():p=output/name;p.write_bytes(content);os.utime(p,ns=(stat.st_atime_ns,stat.st_mtime_ns))
   a=run(root,'restored-verifier-1',['/usr/bin/python3','-B','cad/feed_power/verify_output.py'],True);b=run(root,'restored-verifier-2',['/usr/bin/python3','-B','cad/feed_power/verify_output.py'],True);assert a.returncode==b.returncode==0 and (a.stdout,a.stderr)==(b.stdout,b.stderr)
   result.update({'status':'PASS','cases':cases,'original_R5_verifier_cases':5,'compound_and_unknown_cases':len(mutants)-5,'commands':len(records),'geometry_and_native_files':'UNCHANGED','restored_verifiers_identical':True,'G1':'OPEN'})
 except Exception as e:result.update({'status':'FAIL','cases':cases,'reason':str(e) or repr(e)});print(result['reason'],file=sys.stderr)
 result['sources']={p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'cad/feed_power').glob('*.py')};(DEST/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ('cases','sources')}));return 0 if result['status']=='PASS' else 1
if __name__=='__main__':sys.exit(main())
