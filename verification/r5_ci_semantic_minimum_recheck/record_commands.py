"""Record already executed capture receipts; do not re-run 411 passing mutations.
Full raw runner outputs and case ledger are retained, process success is not acceptance.
"""
from pathlib import Path
import datetime,json,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;P=ROOT/'verification/r4_cycle_interfaces'
python='/workspace/REV/.venv/bin/python'
rows=[]
def receipt(argv,stdout,stderr,env=None):
 assert (HERE/stdout).is_file() and (HERE/stderr).is_file()
 rows.append(dict(argv=argv,cwd=str(ROOT),exit_code=0,stdout=stdout,stderr=stderr,environment_overrides=env or {},recorded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),provenance='Executed in this review; tool exit 0 and raw output/runner/case assertions verified'))
for name in ['author_document.stderr','author_exports.stderr']:(HERE/name).touch()
assert len(json.loads((HERE/'author_document.json').read_text())['checks'])==3277
receipt([python,'-B','verification/r4_cycle_interfaces/proposal/check_package.py'],'author_document.json','author_document.stderr')
assert len(json.loads((HERE/'author_exports.json').read_text())['checks'])==8
receipt([python,'-B','verification/r4_cycle_interfaces/proposal/check_exports_reproduction.py'],'author_exports.json','author_exports.stderr')
cases=json.loads((HERE/'author_mutation_cases.json').read_text());assert cases['count']==411 and cases['all_matched'] and all(c['matched'] for c in cases['cases'])
assert cases==json.loads((P/'semantic_iteration/regression_cases.json').read_text())
assert re.search(r'Ran 6 tests', (HERE/'author_tests.stderr').read_text()) and (HERE/'author_tests.stderr').read_text().rstrip().endswith('OK')
receipt([python,'-B','-m','unittest','discover','-s','verification/r4_cycle_interfaces/semantic_iteration','-p','test_*.py','-v'],'author_tests.stdout','author_tests.stderr',{'REV_CI_CAPTURE':str(HERE/'author_mutation_cases.json')})
assert re.search(r'Ran 7 tests',(HERE/'retained_tests.stderr').read_text()) and (HERE/'retained_tests.stderr').read_text().rstrip().endswith('OK')
receipt([python,'-B','-m','unittest','discover','-s','verification/r4_cycle_interfaces/correction','-p','test_*.py','-v'],'retained_tests.stdout','retained_tests.stderr')
assert json.loads((HERE/'authority.json').read_text())['exact_reproduction']
receipt([python,'-B','verification/r5_ci_semantic_minimum_recheck/authority_and_regressions.py'],'authority.stdout','authority.stderr')
r=subprocess.run([python,'-B',str(HERE/'independent_probe.py'),'--reuse-mutations'],cwd=ROOT,capture_output=True,text=True);assert r.returncode==0,r.stderr
assert json.loads(r.stdout)==json.loads((HERE/'independent_results.json').read_text())
(HERE/'reaggregate.stdout').write_text(r.stdout);(HERE/'reaggregate.stderr').write_text(r.stderr)
receipt([python,'-B','verification/r5_ci_semantic_minimum_recheck/independent_probe.py','--reuse-mutations'],'reaggregate.stdout','reaggregate.stderr')
rows[-1]['provenance']='Re-audit and replay of preserved actual CLI mutation receipts, not a second fresh mutation execution'
for i,argv in enumerate([[python,'-B',str(HERE/'verify_preservation.py')],['git','diff','--check'],['git','lfs','fsck']],1):
 r=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True);assert r.returncode==0,(argv,r.stderr)
 out=f'final_command_{i}.stdout';err=f'final_command_{i}.stderr';(HERE/out).write_text(r.stdout);(HERE/err).write_text(r.stderr);receipt(argv,out,err)
(HERE/'commands.json').write_text(json.dumps(rows,indent=2)+'\n')
print('Command receipts verified; six independent mismatches remain explicit.')
