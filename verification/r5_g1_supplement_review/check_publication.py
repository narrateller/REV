"""Post-publication exact C/H, accepted claim and CI receipt; never merges/renews."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import json
import re
import subprocess
import yaml

ROOT=Path(__file__).resolve().parents[2]
TARGET='fe10c0bc7242fe9d2df3e571c80b4e687f731d7c'
REQUEST='e6ebf7f4df1dbbaa127eaa3c3d00576c1e611658'
CLAIM_MAIN='98d1494334ad5161ea8f56226c770dc762fb59d3'
SESSION='6afb0a73-b16c-8191-a539-9a6685e89034'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--review-C',required=True);ap.add_argument('--handoff-H',required=True);ap.add_argument('--branch',required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();commands=[];checks=[]
    def run(args):
        p=subprocess.run(args,cwd=ROOT,capture_output=True,text=True);commands.append(dict(command=args,exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr))
        if p.returncode:raise RuntimeError(str(args)+': '+p.stderr)
        return p.stdout
    def api(path):return json.loads(run(['gh','api',path]))
    def check(i,ok,actual):checks.append(dict(id=i,result='PASS' if ok else 'FAIL',observed=actual))
    ref='refs/heads/'+a.branch;remote=run(['git','ls-remote','origin',ref]).split();check('remote-H',remote==[a.handoff_H,ref],remote)
    run(['git','fetch','origin',ref]);fetched=run(['git','rev-parse','FETCH_HEAD']).strip();check('fetched-H',fetched==a.handoff_H,fetched)
    parent=run(['git','rev-parse',fetched+'^']).strip();check('H-parent-C',parent==a.review_C,parent)
    parents=run(['git','show','-s','--format=%P',parent]).split();check('C-parents-target-and-claim',parents==[REQUEST,CLAIM_MAIN],parents)
    cap=run(['git','show',f'{fetched}:handoffs/T-r5-g1-supplement-output-review-01/{SESSION}.md']);check('capsule-C-target-H',all(s in cap for s in [a.review_C,TARGET,REQUEST]),'Exact full references present')
    journal=run(['git','show',a.review_C+':reviews/cross_check_log.md']);record=next(yaml.safe_load(x) for x in re.findall(r'```yaml\n(.*?)```',journal,re.S) if 'review_id: REV-R5-G1-SUPPLEMENT-OUTPUT-01-001' in x);check('reviewed-commit-exact',record['reviewed_commit']==TARGET and record['reviewer']['session_id']==SESSION and record['verdict']=='WARNING',dict(reviewed_commit=record['reviewed_commit'],reviewer=record['reviewer']['session_id'],verdict=record['verdict']))
    ci=[]
    for label,sha in [('review_C',a.review_C),('handoff_H',a.handoff_H)]:
        runs=api('repos/narrateller/REV/actions/runs?head_sha='+sha+'&per_page=30')['workflow_runs'];rows=[r for r in runs if r['name']=='Registry & Traceability Gate' and r['event']=='push' and r['head_sha']==sha];row=max(rows,key=lambda r:r['id']) if rows else None
        check(label+'-CI',row is not None and row['status']=='completed' and row['conclusion']=='success',None if row is None else {k:row[k] for k in ['id','head_sha','status','conclusion','html_url']})
        if row:
            jobs=api('repos/narrateller/REV/actions/runs/'+str(row['id'])+'/jobs');steps=[s for j in jobs['jobs'] for s in j['steps'] if s['name'] in ['Check committed evidence without regeneration','Test validator and initializer in isolated temporary copies']];check(label+'-registry-tests',len(steps)==2 and all(s['conclusion']=='success' for s in steps),steps);ci.append(dict(label=label,sha=sha,run_id=row['id'],url=row['html_url'],conclusion=row['conclusion'],jobs=jobs))
    pr=api('repos/narrateller/REV/pulls/55');check('PR55-open-unmerged-exact',pr['state']=='open' and not pr['merged'] and pr['head']['sha']==REQUEST,dict(state=pr['state'],merged=pr['merged'],head=pr['head']['sha']))
    run(['git','fetch','origin','main']);main=run(['git','rev-parse','origin/main']).strip();run(['git','merge-base','--is-ancestor',CLAIM_MAIN,main]);claim=json.loads(run(['git','show',main+':coordination/claims/T-r5-g1-supplement-output-review-01.json']));now=datetime.now(timezone.utc)
    check('fresh-claim-owner-scope-deadline',claim['status']=='ACCEPTED_MAIN' and claim['owner_session']==SESSION and claim['target_C']==TARGET and claim['request_H']==REQUEST and claim['lease_expires_at']=='2026-11-18T01:58:30.990734+00:00' and now<datetime.fromisoformat(claim['lease_expires_at']),dict(main=main,owner=claim['owner_session'],deadline=claim['lease_expires_at'],UTC=now.isoformat()))
    paths=run(['git','ls-tree','-r','--name-only',main,'coordination/claims']).splitlines();owned=[p for p in paths if (lambda d:d.get('owner_session')==SESSION and d.get('status')=='ACCEPTED_MAIN')(json.loads(run(['git','show',main+':'+p])))];check('one-owned-accepted-task',owned==['coordination/claims/T-r5-g1-supplement-output-review-01.json'],owned)
    dirty=run(['git','status','--porcelain']);check('worktree-clean',not dirty,dirty)
    result=dict(checked_at_utc=now.isoformat(),reviewed_target_C=TARGET,request_H=REQUEST,review_C=a.review_C,handoff_H=a.handoff_H,branch=a.branch,remote_main=main,counts={s:sum(x['result']==s for x in checks) for s in ['PASS','FAIL']},checks=checks,CI=ci,commands=commands,G1='OPEN',W02='NO_GO',physical_READY='NO_GO',physical_sections={'4':'NOT_RUN','5':'NOT_RUN','6':'NOT_RUN'})
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(counts=result['counts'],C=a.review_C,H=a.handoff_H,CI=[{k:r[k] for k in ['label','run_id','conclusion','url']} for r in ci])));return any(x['result']=='FAIL' for x in checks)

if __name__=='__main__':raise SystemExit(main())
