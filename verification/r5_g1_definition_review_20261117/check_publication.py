"""Verify published definition-review C/H, fresh explicit scope/claim and CI. No merge/renewal."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import re
import subprocess
import yaml

ROOT=Path(__file__).resolve().parents[2]
TARGET='7e2d5ecff42fe1d09b461e05375924cb644c27c9'
REQUEST='7e4ce7aad8396493da6e2284d29441b46b4abb80'
SCOPE_MAIN='04a6486527c9ba4fd4d22fcf50e0427213443507'
SESSION='6afb0a73-b16c-8191-a539-9a6685e89034'
CLAIM='coordination/claims/T-r5-g1-supplement-output-review-01.json'
AMEND='coordination/scope_amendments/T-r5-g1-supplement-output-review-01/G1-DEFINITION-REGISTER-01.json'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--review-C',required=True);ap.add_argument('--handoff-H',required=True);ap.add_argument('--branch',required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();commands=[];checks=[]
    def run(args):
        p=subprocess.run(args,cwd=ROOT,capture_output=True,text=True);commands.append(dict(command=args,exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr))
        if p.returncode:raise RuntimeError(str(args)+': '+p.stderr)
        return p.stdout
    def api(p):return json.loads(run(['gh','api',p]))
    def check(i,ok,value):checks.append(dict(id=i,result='PASS' if ok else 'FAIL',observed=value))
    def raw(c,p):return subprocess.check_output(['git','show',c+':'+p],cwd=ROOT)
    ref='refs/heads/'+a.branch;remote=run(['git','ls-remote','origin',ref]).split();check('remote-H',remote==[a.handoff_H,ref],remote)
    run(['git','fetch','origin',ref]);head=run(['git','rev-parse','FETCH_HEAD']).strip();check('fetched-H',head==a.handoff_H,head)
    parent=run(['git','rev-parse',head+'^']).strip();check('H-parent-C',parent==a.review_C,parent)
    parents=run(['git','show','-s','--format=%P',parent]).split();check('C-isolated-context-parents',parents==[REQUEST,SCOPE_MAIN],parents)
    cap=run(['git','show',head+':handoffs/T-r5-g1-supplement-output-review-01/'+SESSION+'.md']);check('capsule-exact-references',all(x in cap for x in [a.review_C,TARGET,REQUEST,SCOPE_MAIN]),'Full C/target/request/accepted-scope refs present')
    journal=run(['git','show',a.review_C+':reviews/cross_check_log.md']);record=next(yaml.safe_load(b) for b in re.findall(r'```yaml\n(.*?)```',journal,re.S) if 'review_id: REV-R5-G1-DEFINITION-OUTPUT-01-001' in b)
    check('new-reviewed-commit-exact',record['reviewed_commit']==TARGET and record['reviewer']['session_id']==SESSION and record['verdict']=='WARNING',dict(C=record['reviewed_commit'],reviewer=record['reviewer']['session_id'],verdict=record['verdict']))
    observations=[f for f in record['findings'] if f['id'].startswith('R5-DEF-OBS-')];check('two-open-semantic-observations',len(observations)==2 and all(f['status']=='OPEN' for f in observations),observations)
    ci=[]
    for label,sha in [('review_C',a.review_C),('handoff_H',a.handoff_H)]:
        runs=api('repos/narrateller/REV/actions/runs?head_sha='+sha+'&per_page=30')['workflow_runs'];rows=[r for r in runs if r['name']=='Registry & Traceability Gate' and r['event']=='push' and r['head_sha']==sha];row=max(rows,key=lambda r:r['id']) if rows else None
        check(label+'-CI',row is not None and row['status']=='completed' and row['conclusion']=='success',None if row is None else {k:row[k] for k in ['id','head_sha','status','conclusion','html_url']})
        if row:
            jobs=api('repos/narrateller/REV/actions/runs/'+str(row['id'])+'/jobs');steps=[s for j in jobs['jobs'] for s in j['steps'] if s['name'] in ['Check committed evidence without regeneration','Test validator and initializer in isolated temporary copies']];check(label+'-registry-tests',len(steps)==2 and all(s['conclusion']=='success' for s in steps),steps);ci.append(dict(label=label,sha=sha,run_id=row['id'],url=row['html_url'],conclusion=row['conclusion'],jobs=jobs))
    pr=api('repos/narrateller/REV/pulls/60');check('PR60-open-draft-unmerged',pr['state']=='open' and pr['draft'] and not pr['merged'] and pr['head']['sha']==REQUEST,dict(state=pr['state'],merged=pr['merged'],head=pr['head']['sha']))
    run(['git','fetch','origin','main']);main=run(['git','rev-parse','origin/main']).strip();run(['git','merge-base','--is-ancestor',SCOPE_MAIN,main]);claim=json.loads(raw(main,CLAIM));amend=json.loads(raw(main,AMEND));now=datetime.now(timezone.utc)
    check('fresh-explicit-scope',amend['status']==claim['status']=='ACCEPTED_MAIN' and amend['owner_session']==claim['owner_session']==SESSION and amend['target_C']==TARGET and amend['request_H']==REQUEST and raw(main,AMEND)==raw(SCOPE_MAIN,AMEND),dict(main=main,C=amend['target_C'],H=amend['request_H'],owner=amend['owner_session']))
    check('fresh-base-claim-SHA-and-original-lease',hashlib.sha256(raw(main,CLAIM)).hexdigest()==amend['base_claim_sha256'] and raw(main,CLAIM)==raw(SCOPE_MAIN,CLAIM) and claim['target_C']=='fe10c0bc7242fe9d2df3e571c80b4e687f731d7c' and claim['lease_expires_at']==amend['lease_expires_at']=='2026-11-18T01:58:30.990734+00:00' and now<datetime.fromisoformat(claim['lease_expires_at']),dict(base_target=claim['target_C'],base_sha256=amend['base_claim_sha256'],deadline=claim['lease_expires_at'],UTC=now.isoformat()))
    paths=run(['git','ls-tree','-r','--name-only',main,'coordination/claims']).splitlines();owned=[p for p in paths if (lambda d:d.get('owner_session')==SESSION and d.get('status')=='ACCEPTED_MAIN')(json.loads(raw(main,p)))];check('one-owned-accepted-task',owned==[CLAIM],owned)
    dirty=run(['git','status','--porcelain']);check('worktree-clean',not dirty,dirty)
    result=dict(checked_at_utc=now.isoformat(),reviewed_target_C=TARGET,request_H=REQUEST,accepted_scope_main=SCOPE_MAIN,review_C=a.review_C,handoff_H=a.handoff_H,branch=a.branch,remote_main=main,counts={s:sum(x['result']==s for x in checks) for s in ['PASS','FAIL']},checks=checks,CI=ci,commands=commands,G1='OPEN',W02='NO_GO',physical_READY='NO_GO',physical_sections={'4':'NOT_RUN','5':'NOT_RUN','6':'NOT_RUN'})
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(counts=result['counts'],C=a.review_C,H=a.handoff_H,CI=[{k:x[k] for k in ['label','run_id','conclusion','url']} for x in ci])));return any(x['result']=='FAIL' for x in checks)

if __name__=='__main__':raise SystemExit(main())
