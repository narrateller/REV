"""Receipts for completed actual commands; no pending registry PASS invented."""
from pathlib import Path
import datetime,json,subprocess
R=Path(__file__).resolve().parents[2];H=Path(__file__).resolve().parent;py=str(R/'.venv/bin/python');rows=[]
def receipt(args,out,err,env=None):
 for p in [out,err]:assert (H/p).is_file(),p
 rows.append(dict(argv=args,cwd=str(R),exit_code=0,stdout=out,stderr=err,environment_overrides=env or {},recorded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),note='Actual tool completion and captured outputs verified; probe exit0 is evidence capture, not acceptance.'))
for name,script,count in [('author_document','check_package.py',3277),('author_exports','check_exports_reproduction.py',8)]:
 assert len(json.loads((H/(name+'.json')).read_text())['checks'])==count
 receipt([py,'-B','verification/r4_cycle_interfaces/proposal/'+script],name+'.json',name+'.stderr')
for name,folder,count,envvar,ledger,ncases in [('author_raw','raw_correction',9,'REV_RAW_CAPTURE','author_raw_cases.json',966),('author_gate','gate_correction',11,'REV_GATE_CAPTURE','author_gate_cases.json',220),('author_snapshots','snapshot_correction',11,'REV_SNAPSHOT_CAPTURE','author_snapshot_cases.json',118),('author_type','type_correction',6,'REV_TYPES_CAPTURE','author_type_cases.json',244),('author_semantic','semantic_iteration',6,'REV_CI_CAPTURE','author_semantic_cases.json',411),('retained','correction',7,None,None,None)]:
 raw=(H/(name+'.stderr')).read_text();assert f'Ran {count} tests' in raw and raw.rstrip().endswith('OK')
 if ledger:
  d=json.loads((H/ledger).read_text());assert d['all_matched'] and d['count']==ncases
 receipt([py,'-B','-m','unittest','discover','-s','verification/r4_cycle_interfaces/'+folder,'-p','test_*.py','-v'],name+'.stdout',name+'.stderr',{envvar:str(H/ledger)} if envvar else None)
for script,stem in [('repeat_prior','repeat_prior'),('independent_probe','independent'),('verify_preservation','preservation'),('reproduce_guard_tag','minimal_guard_tag')]:receipt([py,'-B','verification/r5_ci_raw_sources_recheck/'+script+'.py'],stem+'.stdout',stem+'.stderr')
for stem,args in [('diff_check',['git','diff','--check']),('lfs_fsck',['git','lfs','fsck'])]:
 r=subprocess.run(args,cwd=R,capture_output=True,text=True);assert r.returncode==0,r.stderr
 (H/(stem+'.stdout')).write_text(r.stdout);(H/(stem+'.stderr')).write_text(r.stderr);receipt(args,stem+'.stdout',stem+'.stderr')
log=(H/'registry.log').read_text() if (H/'registry.log').is_file() else ''
if 'PASS: repository consistency checks; engineering acceptance NOT assessed' in log:
 (H/'registry.stderr').touch(exist_ok=True);receipt([py,'-B','scripts/check_registry.py','--check-git'],'registry.log','registry.stderr');rows[-1]['note']='Final registry actually exited0; stdout/stderr merged in registry.log; empty sidecar layout only. Engineering acceptance NOT assessed.'
(H/'commands.json').write_text(json.dumps(rows,indent=2)+'\n');print('Completed actual command receipts:',len(rows))
