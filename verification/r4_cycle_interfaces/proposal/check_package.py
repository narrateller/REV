#!/usr/bin/env python3
"""Read-only documentary integrity checks. Never generates or repairs checked files."""
import argparse, csv, hashlib, json, subprocess, sys
from pathlib import Path
import xml.etree.ElementTree as ET
from document_semantics import inspect_semantics
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def inspect(folder=HERE):
 checks=[]
 def check(name,ok):
  checks.append({'id':name,'matched':bool(ok)})
  if not ok:raise ValueError(name)
 audit=read(folder/'input_audit.json');base=audit['base_main']
 claim=read(folder.parent/'claim.json')
 check('accepted_owner_and_unchanged_lease',claim['status']=='ACCEPTED_MAIN' and claim['owner_session']==audit['owner_session'] and claim['lease_expires_at']==claim['proposed_lease_expires_at']==audit['lease_expires_at'])
 check('acceptance_PR45_and_main',claim['acceptance_PR']==45 and claim['acceptance_main']==base)
 baseline=read(folder/'baseline_bindings.json')['rows'];original=read(ROOT/'verification/r4_calculated_layout/source_bindings.json')['rows']
 check('all44_exact_source_rows',len(baseline)==44 and baseline==original)
 manifest=read(folder.parent/'input_manifest.json')['source_bindings']
 check('original_catalog_sha256',digest(ROOT/manifest['path'])==manifest['sha256'])
 for r in baseline:
  src=read(ROOT/r['source']);hits=[a for a in src['inputs']+src['outputs'] if a['id']==r['parameter_id'] and a['revision']==r['revision']]
  check('source:'+r['scenario']+':'+r['parameter_id'],len(hits)==1 and all(r[k]==hits[0][k] for k in ['value','unit','engineering_sha256']) and r['mode']=='fixed-budget')
 for f,h in audit['protected_files_sha256'].items():
  if digest(ROOT/f)!=h:raise ValueError('Protected file changed: '+f)
 check('612_frozen_worktree_files',len(audit['protected_files_sha256'])==612)
 for r in audit['input_blobs']:
  b=subprocess.check_output(['git','show',r['commit']+':'+r['path']],cwd=ROOT)
  if hashlib.sha256(b).hexdigest()!=r['sha256']:raise ValueError('Input blob changed '+r['path'])
 check('17_immutable_source_blobs',len(audit['input_blobs'])==17)
 frozen=read(ROOT/'verification/r4_cycle_contract/contract.json');t={x['id']:x for x in frozen['transitions'] if x['variant'] in ['A','B'] and '-READY' not in x['id']}
 package=read(folder/'permissions.json');actions=package['actions'];ids=[a['id'] for a in actions];lookup={a['id']:a for a in actions}
 check('unique_action_ids',len(ids)==len(set(ids)))
 check('complete_inherited_actions',set(t)<=set(ids))
 for i,o in t.items():
  a=lookup[i];check('inherited:'+i, all(a[k]==o[k] for k in ['entry_guards','completion_guards']) and a['material_from']==o['from_states'] and a['material_to']==o['to_state'] and a['mode']==o['allowed_modes'])
 guard_ids=set(read(folder/'mechanical_guards.json')['guards'])|{g['id'] for g in frozen['guards']}
 for a in actions:
  check('guard_refs:'+a['id'],all(x in guard_ids for x in a['extra_entry_guards']+a['extra_completion_guards']))
 check('no_physical_permission',all(a['permission_actual']=='INDETERMINATE' and a['physical_permission']=='NO_GO' for a in actions))
 check('no_reset_ready_deadlock','RESET_CURRENT' not in lookup['B-RESET']['extra_entry_guards'] and 'RESET_CURRENT' in lookup['B-RESET']['extra_completion_guards'])
 check('no_partial_return_teleport','P_HOME_CURRENT' in lookup['B-COMPACT']['extra_entry_guards'] and 'P_HOME_CURRENT' in lookup['A-COMPACT']['extra_entry_guards'])
 check('explicit_b_unlock_unloaded','B_UNLOADED' in lookup['B-MECH-UNLOCK']['extra_entry_guards'] and 'LOCK_CLEAR' in lookup['B-MECH-STOP-OPEN']['extra_entry_guards'])
 check('feed_before_isolation','D_HOME_CURRENT' in lookup['A-MECH-FEED-ISOLATE']['extra_entry_guards'] and 'G_OPEN_CURRENT' in lookup['B-MECH-DOSE-DELIVER']['extra_entry_guards'])
 check('parent_guard_no_shortcut',lookup['A-MECH-APPROACH']['parent_action_choices']==['A-COMPACT'] and 'No parent may START' in package['substep_parent_rule'])
 checks.extend(inspect_semantics(folder,frozen))
 opts=read(folder/'force_variants.json')['variants'];check('four_unselected_alternatives',{o['id'] for o in opts}=={'A-V1','A-V2','B-V1','B-V2'} and all(o['status']=='ASSUMED_PROPOSAL_NOT_SELECTED' and o['native_geometry']=='NOT_BUILT_NOT_CHECKED' for o in opts))
 unknowns=read(folder/'unknown_inputs.json')['unknowns'];check('unknown_not_zero',all(u['value'] is None and u['status']=='UNKNOWN' and u['unknown_reason'] and u['tolerance'] is None for u in unknowns))
 plan=read(folder/'verification_plan.json');check('no_geometric_pairs_claimed',plan['checked_pairs_this_iteration']==[] and all(s['geometry_result']=='NOT_RUN_INDETERMINATE' and s['pairs'] for s in plan['phases']))
 exp=read(folder/'exports/exports_manifest.json')
 check('export_sources_unchanged',all(digest(folder/n)==h for n,h in exp['sources_sha256'].items()))
 check('exports_unchanged',all(digest(folder/'exports'/n)==h for n,h in exp['exports_sha256'].items()))
 svgs=list((folder/'exports').glob('*.svg'));check('six_well_formed_svg',len(svgs)==6 and all(ET.parse(f).getroot().tag=='{http://www.w3.org/2000/svg}svg' for f in svgs))
 with (folder/'exports/positions_permissions.csv').open() as f:csvrows=list(csv.DictReader(f))
 check('csv_matches_actions',len(csvrows)==len(actions) and all(c['id']==a['id'] and json.loads(c['entry_guards'])==a['entry_guards'] and json.loads(c['poses'])==a['poses'] for c,a in zip(csvrows,actions)))
 return {'execution_status':'COMPLETED','document_checks':'MATCH','checks':checks,'counts':{'actions':len(actions),'inherited':len(t),'source_bindings':len(baseline),'svg':len(svgs),'future_phase_matrices':len(plan['phases']),'future_pairs':sum(len(p['pairs']) for p in plan['phases']),'actually_checked_geometric_pairs':0,'frozen_files':612},'geometry_outcome':'NOT_RUN','physical_READY':'NO_GO','W02':'OPEN_NOT_IMPLEMENTED','G1':'OPEN'}
if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--package',type=Path,default=HERE);a=ap.parse_args()
 try:out=inspect(a.package)
 except Exception as ex:print(json.dumps({'execution_status':'FAILED','document_checks':'MISMATCH','reason':str(ex),'geometry_outcome':'NOT_ASSESSED'},ensure_ascii=False));sys.exit(1)
 print(json.dumps(out,ensure_ascii=False,indent=2))
