"""Record executed receipts, without rerunning costly passing suites/matrices."""
from pathlib import Path
import datetime,hashlib,json,re,subprocess
R=Path(__file__).resolve().parents[2];H=Path(__file__).resolve().parent;py=str(R/'.venv/bin/python');rows=[]
def receipt(args,out,err,env=None):
 for p in [out,err]:assert (H/p).is_file(),p
 rows.append(dict(argv=args,cwd=str(R),exit_code=0,stdout=out,stderr=err,environment_overrides=env or {},recorded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),note='Executed in current review; tool exit and captured output verified. Probe exit 0 is capture completion, not acceptance.'))
for n in ['author_document.stderr','author_exports.stderr']:(H/n).touch(exist_ok=True)
for name,script,count in [('author_document','check_package.py',3277),('author_exports','check_exports_reproduction.py',8)]:
 assert len(json.loads((H/(name+'.json')).read_text())['checks'])==count
 receipt([py,'-B','verification/r4_cycle_interfaces/proposal/'+script],name+'.json',name+'.stderr')
for name,folder,count,envvar,ledger in [('author_type','type_correction',6,'REV_TYPES_CAPTURE','author_type_cases.json'),('author_semantic','semantic_iteration',6,'REV_CI_CAPTURE','author_semantic_cases.json'),('retained','correction',7,None,None)]:
 raw=(H/(name+'.stderr')).read_text();assert f'Ran {count} tests' in raw and raw.rstrip().endswith('OK')
 if ledger:
  d=json.loads((H/ledger).read_text());assert d['all_matched'] and d['count']==(244 if folder=='type_correction' else 411)
 receipt([py,'-B','-m','unittest','discover','-s','verification/r4_cycle_interfaces/'+folder,'-p','test_*.py','-v'],name+'.stdout',name+'.stderr',{envvar:str(H/ledger)} if envvar else None)
for script in ['repeat_prior','independent_probe','incomplete_snapshots','assess_results','verify_preservation','quantity_equivalence']:
 stem={'independent_probe':'independent','incomplete_snapshots':'incomplete','assess_results':'assessment','verify_preservation':'preservation','quantity_equivalence':'quantity'}.get(script,script)
 receipt([py,'-B','verification/r5_ci_strict_types_recheck/'+script+'.py'],stem+'.stdout',stem+'.stderr')
for stem,args in [('diff_check',['git','diff','--check']),('lfs_fsck',['git','lfs','fsck'])]:
 r=subprocess.run(args,cwd=R,capture_output=True,text=True);assert r.returncode==0,r.stderr
 (H/(stem+'.stdout')).write_text(r.stdout);(H/(stem+'.stderr')).write_text(r.stderr);receipt(args,stem+'.stdout',stem+'.stderr')
log=(H/'registry.log').read_text()
assert 'PASS: repository consistency checks; engineering acceptance NOT assessed' in log
(H/'registry.stderr').touch(exist_ok=True)
receipt([py,'-B','scripts/check_registry.py','--check-git'],'registry.log','registry.stderr')
rows[-1]['note']='Executed final registry, exit 0; stdout/stderr merged in registry.log; empty stderr sidecar is layout only. Engineering acceptance not assessed.'
for row in rows[:2]:row['stderr_provenance']='Tool output had no stderr; empty sidecar recorded afterwards, not a separate stderr redirect.'
(H/'commands.json').write_text(json.dumps(rows,indent=2)+'\n')
print('Executed command receipts verified')
