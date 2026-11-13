#!/usr/bin/env python3
"""Document package regression/reproduction only; output to stdout, originals untouched."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,tempfile
HERE=Path(__file__).resolve().parent

def hashes(p):return {str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(p.rglob('*')) if f.is_file()}
def cmd(args):return subprocess.run([sys.executable,'-B',*map(str,args)],capture_output=True,text=True)
def main():
 before=hashes(HERE);checker=HERE/'check_package.py';renderer=HERE/'render_schemes.py';checks=[]
 with tempfile.TemporaryDirectory(prefix='rev-ci-doc-') as tmp:
  tmp=Path(tmp);one=cmd([checker]);two=cmd([checker]);assert one.returncode==two.returncode==0 and one.stdout==two.stdout
  checks.append({'id':'readonly_repeat_identical','matched':True,'original_package_unchanged':hashes(HERE)==before})
  for name in ['repro1','repro2']:
   r=cmd([renderer,'--output-dir',tmp/name]);assert r.returncode==0,r.stderr
  assert hashes(tmp/'repro1')==hashes(tmp/'repro2')==hashes(HERE/'exports')
  checks.append({'id':'explicit_exports_twice_match_saved','matched':True,'export_files':len(hashes(HERE/'exports'))})
  for case in ['missing_svg','corrupt_svg','changed_source_without_export','dropped_inherited_guard','missing_inherited_action','changed_source_value']:
   task=tmp/case;task.mkdir();shutil.copy(HERE.parent/'claim.json',task/'claim.json');shutil.copy(HERE.parent/'input_manifest.json',task/'input_manifest.json');pack=task/'proposal';shutil.copytree(HERE,pack)
   if case=='missing_svg':(pack/'exports/force_A-V1.svg').unlink()
   elif case=='corrupt_svg':(pack/'exports/interface_B.svg').write_text('<invalid>')
   elif case=='changed_source_without_export':
    f=pack/'force_variants.json';f.write_text(f.read_text()+' ')
   elif case in ['dropped_inherited_guard','missing_inherited_action']:
    f=pack/'permissions.json';d=json.loads(f.read_text())
    if case=='dropped_inherited_guard':next(a for a in d['actions'] if a['id']=='B-LOAD')['entry_guards'].remove('RESOURCES_READY')
    else:d['actions']=[a for a in d['actions'] if a['id']!='A-REMOVE']
    f.write_text(json.dumps(d))
   else:
    f=pack/'baseline_bindings.json';d=json.loads(f.read_text());d['rows'][0]['value']=None;f.write_text(json.dumps(d))
   b=hashes(pack);r=cmd([checker,'--package',pack]);assert r.returncode!=0 and json.loads(r.stdout)['document_checks']=='MISMATCH';assert hashes(pack)==b
   checks.append({'id':case,'expected':'MISMATCH_NONZERO_NO_REPAIR','observed':json.loads(r.stdout),'matched':True,'mutated_package_unchanged_by_checker':True})
 assert hashes(HERE)==before
 return {'execution_status':'COMPLETED','document_regressions':'MATCH','checks':checks,'original_files_unchanged':True,'geometry_outcome':'NOT_RUN','physical_READY':'NO_GO','scope':'Document exports/guard coverage/source integrity only; no collision/material/control test or CAD build'}
if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
