"""Authority/claim preparation only. Does not perform PR55 OUTPUT-review.

Read immutable Git metadata plus current remote main/PR/claim state. Never merge,
activate or renew a claim, run a target renderer, or write an engineering result.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
import subprocess

ROOT=Path(__file__).resolve().parents[2]
REL='verification/r5_g1_supplement_claim_20261117/'
TARGET='fe10c0bc7242fe9d2df3e571c80b4e687f731d7c'
H='e6ebf7f4df1dbbaa127eaa3c3d00576c1e611658'
BASE='043271b57aa3d49b6d9b45da03496ea11dad41b1'
SESSION='6afb0a73-b16c-8191-a539-9a6685e89034'
TASK='T-r5-g1-supplement-output-review-01'
DEADLINE='2026-11-18T01:58:30.990734+00:00'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=ROOT/REL/'preflight.json');a=ap.parse_args()
    commands=[];checks=[]
    def run(args):
        p=subprocess.run(args,cwd=ROOT,capture_output=True,text=True)
        commands.append(dict(command=args,exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr))
        if p.returncode:raise RuntimeError(str(args)+': '+p.stderr)
        return p.stdout
    def git(*args):return run(['git',*args])
    def check(i,ok,observed,expected):checks.append(dict(id=i,result='PASS' if ok else 'FAIL',observed=observed,expected=expected))
    def blob(c,p):return subprocess.check_output(['git','show',f'{c}:{p}'],cwd=ROOT)
    def sha(b):return hashlib.sha256(b).hexdigest()
    now=datetime.now(timezone.utc)
    remote=git('ls-remote','origin','refs/heads/main').split()[0]
    git('fetch','origin','main')
    check('fresh-main',remote==git('rev-parse','origin/main').strip()==BASE,remote,BASE)
    check('actual-session',os.environ.get('CODEX_SESSION_ID')==SESSION,os.environ.get('CODEX_SESSION_ID'),SESSION)
    check('request-parent',git('rev-parse',H+'^').strip()==TARGET,git('rev-parse',H+'^').strip(),TARGET)
    ancestry=subprocess.run(['git','merge-base','--is-ancestor',BASE,TARGET],cwd=ROOT).returncode
    check('accepted-main-ancestor',ancestry==0,ancestry,0)
    pr=json.loads(run(['gh','api','repos/narrateller/REV/pulls/55']))
    check('PR55-exact-head-open',pr['state']=='open' and not pr['merged'] and pr['head']['sha']==H and pr['base']['sha']==BASE,dict(state=pr['state'],merged=pr['merged'],head=pr['head']['sha'],base=pr['base']['sha']),'PR55 OPEN/unmerged, exact request H and accepted main')
    open_prs=json.loads(run(['gh','api','repos/narrateller/REV/pulls?state=open&per_page=100']))
    ledger_paths=git('ls-tree','-r','--name-only',BASE,'coordination/claims').splitlines()
    ledgers=[dict(path=p,sha256=sha(blob(BASE,p)),record=json.loads(blob(BASE,p))) for p in ledger_paths]
    r1=next(x['record'] for x in ledgers if x['record']['task_id']=='T-r1-requirements-draft-01')
    intake=next(x['record'] for x in ledgers if x['record']['task_id']=='T-r1-force-inputs-intake-01')
    check('R1-authority-and-deadline',r1['status']=='ACCEPTED_MAIN' and r1['owner_session']=='6afb300b-1540-8191-a5c4-be1a684c20e0' and r1['lease_expires_at']==DEADLINE and now<datetime.fromisoformat(DEADLINE),dict(status=r1['status'],owner=r1['owner_session'],lease_expires_at=r1['lease_expires_at'],observed_at_utc=now.isoformat()),'R1 original accepted scope/deadline active; no renewal')
    check('intake-released',intake['owner_session']=='NONE' and intake['status']=='COMPLETED_DOCUMENTARY_RELEASED',dict(status=intake['status'],owner=intake['owner_session']),'Earlier intake released')
    own_accepted=[x for x in ledgers if x['record'].get('task_id')==TASK and x['record'].get('status')=='ACCEPTED_MAIN']
    live_same_session=[x['path'] for x in ledgers if x['record'].get('owner_session')==SESSION and x['record'].get('status')=='ACCEPTED_MAIN']
    check('R5-claim-absent',not own_accepted,len(own_accepted),'No accepted claim; substantive OUTPUT-review remains NOT_RUN until serialized acceptance')
    check('R5-no-other-active-owned-task',not live_same_session,live_same_session,'No other accepted active task owned by this actual session')
    competing=[dict(number=p['number'],title=p['title'],sha=p['head']['sha']) for p in open_prs if p['number']!=55 and (TASK in p['title'] or 'PR55' in p['title']) and SESSION not in p['head']['ref']]
    check('no-visible-competing-PR',not competing,competing,'No competing visible proposal for exact same task; recheck before acceptance')
    manifest_path='verification/r1_g1_criteria_plan_20261117/review_target_manifest.json'
    manifest=json.loads(blob(TARGET,manifest_path))
    check('target-not-coauthored',SESSION not in manifest['target_author_sessions'],manifest['target_author_sessions'],'Actual reviewer session absent from target authors; upstream disclosed')
    check('manifest-unchanged-at-H',blob(TARGET,manifest_path)==blob(H,manifest_path),sha(blob(TARGET,manifest_path)),'Exact manifest preserved at request H; contents not independently reviewed yet')
    changed=git('diff','--name-only',TARGET,H).splitlines()
    check('H-only-context',set(changed)=={'STATE.md','NEXT_MODEL.md','handoffs/T-r1-requirements-draft-01/6afb300b-1540-8191-a5c4-be1a684c20e0.md','verification/r1_g1_criteria_plan_20261117/R5_review_command.md'},changed,'H changes only request/operational context')
    binding='verification/r4_cycle_interfaces/proposal/baseline_bindings.json'
    bindings=json.loads(blob(BASE,binding))['rows']
    check('binding44-preflight-seal',len(bindings)==44 and blob(BASE,binding)==blob(TARGET,binding),dict(count=len(bindings),sha256=sha(blob(BASE,binding))),'44 complete objects sealed; this is preservation metadata, no engineering review')
    pins=[]
    for c,p in [(BASE,p) for p in ['AGENTS.md','AGENT_PROTOCOL.md','STATE.md','NEXT_MODEL.md','ISSUES_AND_TASKS.md']]+[(TARGET,manifest_path),(H,'verification/r1_g1_criteria_plan_20261117/R5_review_command.md')]:
        pins.append(dict(commit=c,path=p,sha256=sha(blob(c,p))))
    result=dict(observed_at_utc=now.isoformat(),scope='Claim/authority preflight only; NOT an OUTPUT-review',target_C=TARGET,request_H=H,base_main=BASE,actual_session_id=SESSION,checks=checks,counts={s:sum(x['result']==s for x in checks) for s in ['PASS','FAIL']},own_claim_accepted=False,review_status='NOT_RUN_PENDING_ACCEPTED_CLAIM',review_verdict=None,author395_used_as_independent_review=False,prior3890_used_as_independent_review=False,renderer13_status='NOT_RUN',engineering_execution='NOT_STARTED',input_audit_sections={'4':'NOT_RUN','5':'NOT_RUN','6':'NOT_RUN'},G1='OPEN',W02='NO_GO',physical_READY='NO_GO',accepted_ledgers=ledgers,input_seals=pins,open_PRs=[dict(number=p['number'],title=p['title'],branch=p['head']['ref'],sha=p['head']['sha']) for p in open_prs],commands=commands)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(counts=result['counts'],review_status=result['review_status'],own_claim_accepted=False),ensure_ascii=False))
    return any(x['result']=='FAIL' for x in checks)

if __name__=='__main__':raise SystemExit(main())
