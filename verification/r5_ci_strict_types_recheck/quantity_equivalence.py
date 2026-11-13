"""Physical source quantity float->integer equivalence; metadata stays revision integer 1."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,tempfile
R=Path(__file__).resolve().parents[2];H=Path(__file__).resolve().parent;P=R/'verification/r4_cycle_interfaces/proposal'
def hashes(p):return {str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in p.rglob('*') if f.is_file()}
with tempfile.TemporaryDirectory(prefix='r5-quantity-') as tmp:
 dest=Path(tmp);pack=dest/'proposal';shutil.copytree(P,pack)
 for n in ['claim.json','input_manifest.json']:shutil.copy(P.parent/n,dest/n)
 f=pack/'baseline_bindings.json';d=json.loads(f.read_text());row=next(r for r in d['rows'] if r['scenario']=='BASE_A' and r['proposed_cad_field']=='load.return_required');old=row['value'];assert type(old)is float and old.is_integer();row['value']=int(old);f.write_text(json.dumps(d,indent=2)+'\n')
 a=subprocess.run([sys.executable,'-B',str(pack/'render_schemes.py'),'--output-dir',str(pack/'exports')],capture_output=True,text=True);assert a.returncode==0,a.stderr
 before=hashes(pack);m=json.loads((pack/'exports/exports_manifest.json').read_text());assert all(before[n]==h for n,h in m['sources_sha256'].items()) and all(before['exports/'+n]==h for n,h in m['exports_sha256'].items())
 a=subprocess.run([sys.executable,'-B',str(P/'check_package.py'),'--package',str(pack)],capture_output=True,text=True);assert before==hashes(pack)
 (H/'quantity_check.json').write_text(a.stdout);d=json.loads(a.stdout)
 result=dict(expected='MATCH',actual=d.get('document_checks'),exit_code=a.returncode,matched=a.returncode==0,source_field='BASE_A/load.return_required',original_json_type='float',mutated_json_type='integer',unchanged_numeric_value=old,metadata_revision_unchanged=True,fresh_hashes=True,readonly=True)
 (H/'quantity_result.json').write_text(json.dumps(result,indent=2)+'\n');assert result['matched'],d
 print('Physical quantity float->integer after fresh export: MATCH, revisions unchanged')
