"""Documentary identity regression and preservation checks, not physical validation."""
import hashlib
import json
import re
import subprocess
from pathlib import Path
from render_register import HERE, SOURCE, render

ROOT = HERE.parents[1]
checks = []
def check(name, ok):
    checks.append({'id': name, 'status': 'PASS' if ok else 'FAIL'})
def labels(text):
    return re.findall(r'^Документальный метод: (\S+) / (.+?)\. Будущий предикат', text, re.M)
methods = json.loads((SOURCE/'method_catalog.json').read_text())['rows']
defs = json.loads((SOURCE/'definition_register.json').read_text())['rows']
byid = {m['method_id']:m for m in methods}
expected = [(r['definition_method_id'], byid[r['definition_method_id']]['revision_label']) for r in defs]
summary = (HERE/'definition_register.md').read_text()
observed = labels(summary)
check('all22_controlled_method_labels', len(observed)==22 and observed==expected)
for r,m in zip(defs,methods):
    check(r['requirement_id']+':matched_identity', r['definition_method_id']==m['method_id'] and r['requirement_id']==m['requirement_id'] and r['validation_id']==m['validation_id'])
    check(r['requirement_id']+':rendered_revision', (m['method_id'],m['revision_label']) in observed)
common=json.loads((SOURCE/'method_catalog.json').read_text())['common_protocol']
check('common_protocol_identity_from_JSON',f"## {common['id']} / {common['revision_label']}" in (HERE/'verification_plan.md').read_text())
old = (SOURCE/'definition_register.md').read_text()
old_labels = dict(labels(old))
check('oracle_detects_original_OBS03', [m['method_id'] for m in methods if old_labels.get(m['method_id'])!=m['revision_label']]==['DM-02','DM-03'])
restored = summary
for mid in ['DM-02','DM-03']:
    restored=restored.replace(f'Документальный метод: {mid} / DRAFT-02.',f'Документальный метод: {mid} / DRAFT-01.')
check('only_two_summary_labels_changed', restored==old and summary!=old)
for name,text in render().items():
    check('render_MATCH:'+name,(HERE/name).read_text()==text)
    if name!='definition_register.md':check('unchanged_output:'+name,(HERE/name).read_bytes()==(SOURCE/name).read_bytes())
# A synthetic revision-only change must propagate for a different method too; no file/data mutation.
import copy
import render_register as renderer
original_load=renderer.load
changed=copy.deepcopy(json.loads((SOURCE/'method_catalog.json').read_text()))
changed['rows'][3]['revision_label']='SYNTHETIC-REVISION-CHECK'
try:
    renderer.load=lambda name: changed if name=='method_catalog.json' else original_load(name)
    synthetic=labels(renderer.render()['definition_register.md'])
    expected_synthetic=list(expected);expected_synthetic[3]=('DM-04','SYNTHETIC-REVISION-CHECK')
    check('metadata_revision_propagates_without_hardcode',synthetic==expected_synthetic)
finally:renderer.load=original_load
manifest=json.loads((HERE/'input_manifest.json').read_text())
for row in manifest['inputs']:
    check('frozen:'+row['path'],hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['sha256'])
for folder,tree in manifest['protected_trees'].items():
    current=subprocess.check_output(['git','rev-parse','HEAD:'+folder],cwd=ROOT,text=True).strip()
    diff=subprocess.check_output(['git','diff',manifest['working_base'],'--name-only','--',folder],cwd=ROOT,text=True).strip()
    check('protected_tree:'+folder,current==tree and not diff)
status=json.loads((HERE/'observation_status.json').read_text())
check('OBS03_not_self_closed',status['OBS03']=='OPEN_PENDING_INDEPENDENT_RECHECK' and status['author_closed_observation'] is False and status['new_independent_review']=='NOT_RUN')
check('historical_closures_bound_to_prior_C',all(r['status']=='CLOSED_DOCUMENTARY_EXACT_C' and r['exact_C']=='97f58fd437947e26963bdbbc2f2d89df7438e8cc' for r in status['historical_closures'].values()))
result={'scope':'Author renderer-identity/preservation checks; includes a synthetic metadata-only label regression; not independent closure or engineering execution','counts':{'PASS':sum(c['status']=='PASS' for c in checks),'FAIL':sum(c['status']=='FAIL' for c in checks)},'checks':checks}
print(json.dumps(result,ensure_ascii=False,indent=2))
raise SystemExit(bool(result['counts']['FAIL']))
