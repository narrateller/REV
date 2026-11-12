"""Value-level stale derived evidence and missing mandatory service; manifest
hashes are refreshed explicitly by harness, never by verifier. COPY only.
"""
import gzip,hashlib,io,json,os,subprocess,sys
from pathlib import Path
R=Path(sys.argv[1]).resolve();dest=Path(sys.argv[2]);assert not dest.is_relative_to(R);P=R/'cad/build/feed_power';records=[];cases=[]
names=('interval_rows.json.gz','classifications.jsonl.gz','service_report.json','service_semantics.json','assessment.md','service_scenes.json.gz','work_and_extra.json.gz','publication_manifest.json');backup={n:((P/n).read_bytes(),(P/n).stat()) for n in names}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def snapshot():return {str(p.relative_to(R)):(sha(p),p.stat().st_size,p.stat().st_mtime_ns) for p in R.rglob('*') if p.is_file() and not {'.git','.venv','__pycache__'}&set(p.parts)}
def restore():
 for n,(b,st) in backup.items():(P/n).write_bytes(b);os.utime(P/n,ns=(st.st_atime_ns,st.st_mtime_ns))
def seal():
 m=json.loads(backup['publication_manifest.json'][0])
 for n in names:
  if n!='publication_manifest.json':m['sha256']['cad/build/feed_power/'+n]=sha(P/n)
 (P/'publication_manifest.json').write_text(json.dumps(m,indent=2)+'\n')
def run(label,script,args=(),readonly=True,expected=1):
 before=snapshot();p=subprocess.run(['/usr/bin/python3','-B','cad/feed_power/'+script+'.py',*args],cwd=R,text=True,capture_output=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'});after=snapshot();changed=[n for n in before.keys()|after.keys() if before.get(n)!=after.get(n)];records.append({'label':label,'command':p.args,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'read_only_required':readonly,'file_changes':changed});dest.write_text(json.dumps({'cases':cases,'commands':records},indent=2)+'\n');print(label,p.returncode,flush=True);assert p.returncode==expected,(label,p.stdout,p.stderr)
 if readonly:assert not changed,(label,changed)
 return p
# Keep row count and identity/order, change only a geometric result's value.
rows=json.loads(gzip.decompress(backup['interval_rows.json.gz'][0]));r=next(r for r in rows if r['status']=='POSITIVE_BOUND_OVERLAP');identity={k:r[k] for k in ('variant','case','phase','pair')};r.clear();r.update(identity,status='NO_POSITIVE_VOLUME_ON_INTERVAL');(P/'interval_rows.json.gz').write_bytes(gzip.compress(json.dumps(rows,separators=(',',':')).encode(),mtime=0));del rows;seal();p=run('forged_interval_value_same_row_count','verify_output');v=json.loads(p.stdout);assert v['service_semantics']['test_evaluation']=='PASS' and 'stale interval result' in v['reason'];cases.append({'id':'forged_interval_value_same_row_count','result':'FAIL at fresh value comparison, not hash/coverage','reason':v['reason']});restore()
# Preserve stream size/order; hide a proven legacy positive classification.
buf=io.BytesIO();done=False
with gzip.GzipFile(fileobj=buf,mode='wb',mtime=0) as stream:
 for line in gzip.decompress(backup['classifications.jsonl.gz'][0]).splitlines(keepends=True):
  r=json.loads(line)
  if not done and r['case']=='service_doser_slide' and r['class']=='PENETRATION':r['class']='CLEAR';line=(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n').encode();done=True
  stream.write(line)
assert done;(P/'classifications.jsonl.gz').write_bytes(buf.getvalue());seal();p=run('hidden_legacy_collision_class_same_row_count','verify_output');v=json.loads(p.stdout);assert v['service_semantics']['test_evaluation']=='PASS' and 'stale classification' in v['reason'];cases.append({'id':'hidden_legacy_collision_class_same_row_count','result':'FAIL at recomputed classification','reason':v['reason']});restore()
report=json.loads(backup['service_report.json'][0]);r=next(r for r in report['service_scenes'] if r['case']=='service_doser_slide');r['limited_geometry_success']=True;r['geometric_path_outcome']='CONFIRMED_NO_POSITIVE_VOLUME';(P/'service_report.json').write_text(json.dumps(report,indent=2)+'\n');seal();p=run('report_negative_expectation_forged_to_path_success','verify_output');v=json.loads(p.stdout);assert 'saved report differs' in v['reason'];cases.append({'id':'report_negative_expectation_forged_to_path_success','result':'FAIL: report contradicts fresh BLOCKED result','reason':v['reason']});restore()
# Remove one required scene from both source copies, not just one duplicate.
for name in ('service_scenes.json.gz','work_and_extra.json.gz'):
 scenes=json.loads(gzip.decompress(backup[name][0]));scenes=[s for s in scenes if (s['variant'],s['case'])!=('B','service_fp_motor')];(P/name).write_bytes(gzip.compress(json.dumps(scenes,sort_keys=True,separators=(',',':')).encode(),mtime=0))
seal();p=run('missing_required_service/calculation','service_semantics');sem=json.loads(p.stdout);assert sem['test_evaluation']=='FAIL' and ['B','service_fp_motor'] in sem['missing_required_services']
p=run('missing_required_service/report','present',('--report-only',),False);report=json.loads((P/'service_report.json').read_text());assert report['test_evaluation']=='FAIL' and ['B','service_fp_motor'] in report['missing_required_services'];seal()
p=run('missing_required_service/verifier','verify_output');v=json.loads(p.stdout);assert not v['service_semantics']['complete_required_service_set']
p=run('missing_required_service/reanalysis','generate',('--reanalyze',));g=json.loads(p.stderr);assert g['test_evaluation']=='FAIL' and ['B','service_fp_motor'] in g['service_semantics']['missing_required_services'];cases.append({'id':'missing_required_service','all_four_CLI_exits':[1,1,1,1],'missing':['B','service_fp_motor'],'no_auto_repair':True});restore();dest.write_text(json.dumps({'cases':cases,'commands':records},indent=2)+'\n');print('PASS: stale derived values/report and missing service rejected without repair')
