"""Repeatable saved-package read-only and isolated generation checks."""
import argparse,datetime,hashlib,json,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];AUDIT=ROOT/'verification/r4_calculated_layout';OUT=ROOT/'cad/build/calculated_layout'
def save(name,value):(AUDIT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def snapshot():
    m=json.loads((AUDIT/'input_manifest.json').read_text());files=set(m['sources'])-{'ISSUES_AND_TASKS.md'};files.update(m['prior_publication_manifest_80_files']);files.update(str(p.relative_to(ROOT)) for folder in (ROOT/'cad/calculated_layout',OUT) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    return {n:[hashlib.sha256((ROOT/n).read_bytes()).hexdigest(),(ROOT/n).stat().st_size,(ROOT/n).stat().st_mtime_ns] for n in sorted(files)}
def command(args):
    p=subprocess.run(args,cwd=ROOT,text=True,capture_output=True)
    return {'argv':args,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
def readonly():
    before=snapshot();results=[]
    for i,extra in enumerate([[],[],['--require-clear']],1):
        a=snapshot();r=command(['/usr/bin/python3','-B','cad/calculated_layout/pipeline.py','verify']+extra);r.update(files_unchanged=a==snapshot(),files_checked=len(a));results.append(r);save(f'verifier-{i}.json',r);print('verifier',i,r['exit_code'],r['files_unchanged'],flush=True)
        if r['exit_code']!=(2 if extra else 0):break
    r={'observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'commands':results,'all_files_unchanged':before==snapshot(),'repeated_stdout_stderr_equal':len(results)>1 and results[0]['stdout']==results[1]['stdout'] and results[0]['stderr']==results[1]['stderr']};save('read_only_verification.json',r)
    assert len(results)==3 and r['all_files_unchanged'] and r['repeated_stdout_stderr_equal'] and [x['exit_code'] for x in results]==[0,0,2]
def repeat():
    before=snapshot();results={}
    with tempfile.TemporaryDirectory(prefix='rev-cl-final-repeat-') as temp:
        out=Path(temp)/'package'
        for action in ('generate','verify'):
            r=command(['/usr/bin/python3','-B','cad/calculated_layout/pipeline.py',action,'--out',str(out)]);results[action]=r;print('repeat',action,r['exit_code'],flush=True)
            if r['exit_code']:break
        if len(results)==2 and all(x['exit_code']==0 for x in results.values()):
            compared={}
            for v in 'AB':
                a=json.loads((OUT/v/'manifest.json').read_text());b=json.loads((out/v/'manifest.json').read_text());keys=['objects','query_volumes','reference_objects','source_aliases','source_edit_probe','spreadsheet_parameters']
                compared[v]={'native_semantic_fields':{k:a[k]==b[k] for k in keys},'results_equal':(OUT/v/'results.json').read_bytes()==(out/v/'results.json').read_bytes(),'scenes_equal':(OUT/v/'scenes.json.gz').read_bytes()==(out/v/'scenes.json.gz').read_bytes(),'png_equal':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()==hashlib.sha256((out/v/p.name).read_bytes()).hexdigest() for p in (OUT/v).glob('*.png')}}
            results['comparison']=compared
    results['original_files_unchanged']=before==snapshot();results['test_result']='PASS' if 'comparison' in results and results['original_files_unchanged'] and all(all(x['native_semantic_fields'].values()) and x['results_equal'] and x['scenes_equal'] and all(x['png_equal'].values()) for x in results['comparison'].values()) else 'FAIL';save('repeatability.json',results);assert results['test_result']=='PASS'
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['readonly','repeat','all'],default='all',nargs='?');args=parser.parse_args()
    if args.action in ('readonly','all'):readonly()
    if args.action in ('repeat','all'):repeat()
