"""R5 read-only reproduction; writes logs only in this review directory."""
import datetime,hashlib,json,os,platform,subprocess,sys
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[2]; HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
from repo_support import flatten,engineering_sha
OUT=ROOT/'verification/r3_power_reconcile'
C='c115f75fd900525d9ddc89d85e097ac5a0f00bc1'
H='1344c1a62b83503a73ab85e5c5fff78907eb820d'
OLD='8a1ad4199fea09d1157972d7aa28eaad1e8e0337'
R5='d92cebd5a539d6845fe114515154e79c639bcb7e'
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
identity=json.loads((OUT/'inputs/identity.json').read_text())
manifest=json.loads((OUT/'sha256.json').read_text())
assert all(digest(ROOT/p)==h for p,h in manifest.items())
assert all(digest(ROOT/p)==h for p,h in identity['frozen_files'].items())
legacy=yaml.safe_load(subprocess.check_output(['git','show',OLD+':params/registry.yaml'],cwd=ROOT))
original=flatten(legacy); current=flatten(yaml.safe_load((ROOT/'params/registry.yaml').read_text()))
assert all(current[k]==v for k,v in original.items())
assert all(engineering_sha(current[k])==v for k,v in identity['original_engineering_hashes'].items())
for p,h in identity['frozen_files'].items():
    assert hashlib.sha256(subprocess.check_output(['git','show',OLD+':'+p],cwd=ROOT)).hexdigest()==h
review_blob=subprocess.check_output(['git','show',R5+':verification/r5_r3_parametric_review/review.md'],cwd=ROOT)
assert review_blob==(OUT/'inputs/r5_review.txt').read_bytes()
paths=set(manifest)|set(identity['frozen_files'])
for folder in ('verification/r3_power_reconcile','verification/r3_parametric_sizing'):
    paths.update(str(p.relative_to(ROOT)) for p in (ROOT/folder).rglob('*') if p.is_file())
def snapshot():
    return {p:{'sha256':digest(ROOT/p),'size':(ROOT/p).stat().st_size,'mtime_ns':(ROOT/p).stat().st_mtime_ns} for p in sorted(paths)}
before=snapshot()
commands=[
 ['.venv/bin/python','-B','scripts/rev_parametric.py'],
 ['.venv/bin/python','-B','scripts/rev_parametric.py'],
 ['.venv/bin/python','-B','scripts/rev_power_reconcile.py'],
 ['.venv/bin/python','-B','scripts/rev_power_reconcile.py'],
 ['.venv/bin/python','-B','-m','unittest','discover','-s','tests','-p','test_rev_power_reconcile.py','-v'],
 ['.venv/bin/python','-B','-m','unittest','discover','-s','tests','-v'],
 ['.venv/bin/python','-B','scripts/check_registry.py','--check-git'],
 ['git','diff','--check'],
 ['gh','pr','view','39','--json','state,headRefOid,headRefName,baseRefName,url'],
 ['gh','pr','view','38','--json','state,mergeCommit,mergedAt,url'],
 ['git','ls-remote','origin','refs/heads/main']]
checks=[]
for i,cmd in enumerate(commands,1):
    proc=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
    log=f'command_{i:02}.log'
    (HERE/log).write_text('$ '+' '.join(cmd)+'\nexit='+str(proc.returncode)+'\nSTDOUT\n'+proc.stdout+'\nSTDERR\n'+proc.stderr)
    checks.append({'argv':cmd,'exit':proc.returncode,'log':log})
    assert proc.returncode==0,(cmd,proc.stderr)
after=snapshot(); assert before==after
for a,b in ((1,2),(3,4)):assert (HERE/f'command_{a:02}.log').read_text()==(HERE/f'command_{b:02}.log').read_text()
objects=[]
for sha in (OLD,R5,C,H,'5fdc50bbc8e83241ad2f8754860a503f5de9f418','8867521a83bd4608886d81678683ea89cce7e4a3'):
    objects.append({'sha':sha,'type':subprocess.check_output(['git','cat-file','-t',sha],cwd=ROOT,text=True).strip()})
for a,b in ((OLD,C),(C,H),('5fdc50bbc8e83241ad2f8754860a503f5de9f418','8867521a83bd4608886d81678683ea89cce7e4a3')):
    assert subprocess.run(['git','merge-base','--is-ancestor',a,b],cwd=ROOT).returncode==0
record={'observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'session_id':os.getenv('CODEX_SESSION_ID'),'runtime_session_id':os.getenv('CODEX_CAAS_SESSION_ID'),
        'python':sys.version,'pyyaml':yaml.__version__,'platform':platform.platform(),
        'objects':objects,'C_to_H_diff':subprocess.check_output(['git','diff','--name-only',C,H],cwd=ROOT,text=True).splitlines(),
        'author_manifest_hashes':len(manifest),'frozen_files':len(identity['frozen_files']),
        'all_original_definitions_unchanged':len(original),'original_review_blob_sha256':hashlib.sha256(review_blob).hexdigest(),
        'protected_files':len(paths),'before':before,'after':after,'commands':checks,
        'old_and_new_readonly_twice_identical':True,'protected_sha_size_mtime_unchanged':True}
(HERE/'reproduction.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k not in ('objects','before','after','commands')},ensure_ascii=False))
