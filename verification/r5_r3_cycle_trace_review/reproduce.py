"""R5: preserved-package reproduction only; no CAD builds or physical trials."""
import datetime,hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
SRC=ROOT/'verification/r3_cycle_trace'
C='43f03359fabe2b664935b17f9ac7851504093ece';H='94706e091ba8b27b74b321b6f0ca00b3ea7fd176'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
calc=json.loads((ROOT/'verification/pr39_integration/preservation.json').read_text())['protected_files']
old_reviews=json.loads((SRC/'result_preservation.json').read_text())['preserved_R5_files']
sources=json.loads((SRC/'sources.json').read_text())['sources']
paths=set(calc)|set(old_reviews)|{v['path'] for v in sources.values()}
paths.update(str(p.relative_to(ROOT)) for p in SRC.rglob('*') if p.is_file())
for p,v in calc.items():assert sha(ROOT/p)==v['sha256']
for p,v in old_reviews.items():assert sha(ROOT/p)==v['sha256']
for v in sources.values():assert sha(ROOT/v['path'])==v['sha256']
def snapshot():return {p:{'sha256':sha(ROOT/p),'size':(ROOT/p).stat().st_size,'mtime_ns':(ROOT/p).stat().st_mtime_ns} for p in sorted(paths)}
before=snapshot();commands=[
 ['.venv/bin/python','-B','verification/r3_cycle_trace/verify_trace.py'],
 ['.venv/bin/python','-B','verification/r3_cycle_trace/render_documents.py'],
 ['sha256sum','-c','verification/r3_cycle_trace/artifacts.sha256'],
 ['.venv/bin/python','-B','scripts/rev_parametric.py'],
 ['.venv/bin/python','-B','scripts/rev_power_reconcile.py'],
 ['.venv/bin/python','-B','scripts/check_registry.py','--check-git'],
 ['git','diff','--check'],
 ['gh','pr','view','42','--json','state,headRefOid,headRefName,baseRefName,url'],
 ['gh','pr','view','41','--json','state,mergeCommit,mergedAt,url'],
 ['git','ls-remote','origin','refs/heads/main']]
checks=[]
for i,cmd in enumerate(commands,1):
 proc=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True);log=f'command_{i:02}.log'
 (HERE/log).write_text('$ '+' '.join(cmd)+'\nexit='+str(proc.returncode)+'\nSTDOUT\n'+proc.stdout+'\nSTDERR\n'+proc.stderr)
 checks.append({'argv':cmd,'exit':proc.returncode,'log':log});assert proc.returncode==0,(cmd,proc.stderr)
after=snapshot();assert before==after
record={'observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'session_id':os.getenv('CODEX_SESSION_ID'),'runtime_session_id':os.getenv('CODEX_CAAS_SESSION_ID'),
 'reviewed_C':C,'handoff_H':H,'python':sys.version,'calculation_files':len(calc),'historical_R5_files':len(old_reviews),'PDF_files':len(sources),'protected_files':len(paths),'unchanged_sha_size_mtime':True,'before':before,'after':after,'commands':checks}
(HERE/'reproduction.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k not in ('before','after','commands')},ensure_ascii=False))
