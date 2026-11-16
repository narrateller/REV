"""Independent R5 documentary oracle. No force/geometry/physical calculation.

Expectations below are derived from upstream task, source meanings and authority;
author renderer/verifier are not imported. Immutable C is always the target.
Writes only its own new evidence file, refusing to overwrite an existing one.
"""
import argparse
import datetime
import functools
import hashlib
import json
import re
import subprocess
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
C = 'b840dfd5444da2bf62483b7f4a6069d2bb255b71'
H = '9433ef749df14a3bbf8ea32331e2f895fd5bf7aa'
COMMAND = 'c2c16d1ac4f5a4da44f407872733eba90d08a4a2'
AUTH = '80f1028c25d1c4344c0115b7908e02346d895701'
BASE = 'f731910273b47f46c6d45114cecd76de6fa8adf9'
PR49 = 'cd1c08efc4bcd3f50ceeb132a3e8747e9c8c38b9'
PRIOR = '45caac78f00ab1535387bb5ed8d7f17caf9afc1f'
PKG = 'verification/r4_force_geometry/symbolic_20261116/'
SESSION = '6afb0a73-b16c-8191-a539-9a6685e89034'
def git(*args):
    return subprocess.check_output(['git','-C',str(ROOT),*args])
@functools.lru_cache(None)
def blob(commit,path):
    return git('show',commit+':'+path)
def j(path,commit=C):
    return json.loads(blob(commit,path))
def sha(b):
    return hashlib.sha256(b).hexdigest()
def params(data):
    return {k:v for domain in data['domains'].values() for k,v in domain.items()}
def leaves(x,path=''):
    if isinstance(x,dict):
        for k,v in x.items():yield from leaves(v,path+'/'+k)
    elif isinstance(x,list):
        for i,v in enumerate(x):yield from leaves(v,path+'/'+str(i))
    else:yield path,x

# Independent interface contract: intended link, source scope, missing arguments,
# data owners, and meaning of the next check. These are textual predicates only.
CONTRACT = {
 'datum_motion': ('KIN', ('привязк','поз','e_y'), {'R4','R3'}, 'Камерная база и осевая гипотеза; полные/частичные позы и фактические базы неизвестны.'),
 'cylinder_frame': ('AXIAL', ('COTS','DOF','боков'), {'R3','R4','R6','R5'}, 'Монтаж корпуса к раме; bore/rod не определяют COTS, монтаж, боковую нагрузку или контакты.'),
 'rod_grip': ('AXIAL', ('геометр','контакт','материал'), {'R3','R4','R6','R5'}, 'Захват штока должен передавать оба знака; толкание не доказывает растягиваемый контакт.'),
 'grip_transfer': ('MOMENT', ('e_y','двусторон','ос'), {'R4','R3','R5','R6'}, 'Полный спрос через траверсу/портал; пространственный вынос и локальные оси не определены.'),
 'transfer_carrier': ('KIN', ('L_free_rod','L_free_carrier','опор'), {'R4','R3','R5'}, 'Носитель отдельный от штока; max RAW не функция свободной длины и не схема закрепления.'),
 'carrier_punch': ('AXIAL', ('сечен','захват','контакт'), {'R4','R3','R6','R5'}, 'Отдельный стык носитель–пуансон, местные усилия и двусторонние контактные стороны неизвестны.'),
 'carrier_guides': ('GUIDE', ('шаг','плоскост','жёстк'), {'R4','R3','R5'}, 'Изолированная моментная пара не является полными реакциями реальной многоопорной системы.'),
 'guides_frame': ('GUIDE', ('креп','преднатяг','плоскост'), {'R4','R6','R3','R5'}, 'Опоры направляющих передают обратные силы на раму, но крепления/срез/отрыв и совместность не проверены.'),
 'material_reaction': ('AXIAL', ('фазов','контакт','удерж'), {'R2','R3','R4','R5'}, 'Контактная реакция A/B условна; собственный контакт по фазам, а не peak во всех состояниях.'),
 'reaction_frame': ('MOMENT', ('опор','контакт','рам'), {'R4','R3','R6','R5','R2'}, 'Реакционный узел замыкается на раму только при фактическом контакте/удержании; отпускание отдельно.'),
 'sections_stability': ('EULER', ('I_y','I_z','L_free','критер'), {'R4','R6','R5','R1','R3'}, 'Раздельные шток/носитель/портал/рама, главные плоскости и критерии; capacity/margin неизвестны.'),
 'envelopes_service': (None, ('swept','подач','допуск'), {'R4','R3','R6','R5'}, 'Только наследованное требование полного swept-volume и обслуживания; collision CLEAR не установлен.'),
 'receiver_cycle': (None, ('приём','фазов','старта'), {'R1','R2','R3','R4','R5'}, 'Выход/остатки/возврат/reset не следуют из stroke/timing; реальный READY запрещён.')}

def run(output):
    if output.exists():raise SystemExit('fresh output required')
    checks=[]; findings=[]; rows_evidence=[]
    def check(name,ok,expected,observed):
        checks.append(dict(id=name,result='PASS' if ok else 'FAIL',expected=expected,observed=observed))
        return ok
    def must(name,ok,expected,observed):
        if not check(name,ok,expected,observed):raise AssertionError(name)
    git('merge-base','--is-ancestor',PR49,BASE)
    git('merge-base','--is-ancestor',BASE,C)
    must('H_direct_child',git('rev-parse',H+'^').decode().strip()==C,'request H child of exact C',H)
    must('H_scope',set(git('diff','--name-only',C,H).decode().splitlines())=={
        'STATE.md','NEXT_MODEL.md','handoffs/T-r4-force-geometry-01/6afb4750-7918-8191-8569-77b5b0c41050.md',
        PKG+'review_request.md',PKG+'review_request.json'},'only request/handoff files',H)
    request=j(PKG+'review_request.json',H)
    must('actual_session_not_author',SESSION not in request['author_sessions']+request['excluded_author_sessions'],
         'Reviewer is not an R4/R1 target coauthor; upstream disclosure in identity.json',request['excluded_author_sessions'])
    must('exact_request',request['target_C']==C and request['authority_C']==AUTH,'target and authority exact',request['target_C'])
    claim=j('verification/r4_force_geometry/claim.json')
    baseline_claim=j('verification/r4_force_geometry/claim.json',BASE)
    for x in (claim,baseline_claim):
        must('owner_lease:'+str(x['heartbeat_utc']),x['owner_session']=='6afb4750-7918-8191-8569-77b5b0c41050'
             and x['lease_expires_at']=='2026-11-17T17:44:00Z' and x['status']=='ACCEPTED_MAIN',
             'accepted same owner and original deadline',{'owner':x['owner_session'],'lease':x['lease_expires_at']})
    deadline=datetime.datetime.fromisoformat(claim['lease_expires_at'].replace('Z','+00:00'))
    for name in ('heartbeat_start.json','heartbeat_end.json','heartbeat_precommit.json'):
        event=j(PKG+name);t=datetime.datetime.fromisoformat(event['recorded_at_utc'])
        must('author_time:'+name,t<deadline and event['lease_expires_at']==claim['lease_expires_at'] and not event['lease_extended'],
             'author evidence within unchanged lease',event)
    audit=j('verification/r4_force_geometry/input_audit.json')
    must('audit_preserved',blob(C,'verification/r4_force_geometry/input_audit.json')==blob(PRIOR,'verification/r4_force_geometry/input_audit.json'),
         'prior audit immutable',PRIOR)
    must('audit_456_NOT_RUN',all(x['status']=='NOT_RUN' for x in audit['items'] if x['section'] in (4,5,6)),
         'no physical/numerical audit performed',[(x['section'],x['status']) for x in audit['items']])
    manifest=j('verification/r4_force_geometry/input_manifest.json')
    must('54_inputs',len(manifest['inputs'])==54,'54 pinned inputs',len(manifest['inputs']))
    for item in manifest['inputs']:
        p=item['path'];original=blob(item['commit'],p)
        must('pinned:'+p,sha(original)==item['sha256'] and all(blob(x,p)==original for x in (BASE,C,H)),
             'source/base/C/H SHA256 identical',item)
    protected=[]
    for p,tree in manifest['protected_trees'].items():
        must('tree:'+p,all(git('rev-parse',x+':'+p).decode().strip()==tree for x in (BASE,C,H)),
             '12 protected tree identities',tree)
        for f in git('ls-tree','-r','--name-only',C,p).decode().splitlines():
            raw=blob(C,f);current=(ROOT/f).read_bytes()
            if raw.startswith(b'version https://git-lfs.github.com/spec/v1\n'):
                oid=re.search(rb'oid sha256:([a-f0-9]{64})',raw).group(1).decode()
                okay=sha(current)==oid
            elif f=='reviews/cross_check_log.md':okay=current.startswith(raw)
            else:okay=current==raw
            must('worktree:'+f,okay,'protected original content; only appended reviewer record permitted',sha(current))
            protected.append(f)
    catalog=j(PKG+'source_catalog.json');sources={}
    for alias,s in catalog.items():
        raw=blob(s['commit'],s['path']);sources[alias]=raw
        must('source:'+alias,sha(raw)==s['sha256'] and git('rev-parse',s['commit']+':'+s['path']).decode().strip()==s['git_blob'],
             'exact source commit/path/blob/hash',s)
    original=params(yaml.safe_load(sources['REG']))
    scoped=params(yaml.safe_load(sources['RAW']))
    raw_ids={k:v for k,v in scoped.items() if k.startswith('R3F_') and v['lifecycle']=='RAW'}
    must('84_RAW',len(raw_ids)==84 and all(x['value'] is None and x['unknown_reason'] for x in raw_ids.values()),
         'source RAW/null without promotion',len(raw_ids))
    bindings=json.loads(sources['BIND'])['rows']
    must('44_bindings',len(bindings)==44 and all(r['mode']=='fixed-budget' and r['cad_application']=='NOT_APPLIED' for r in bindings),
         '44 complete frozen source bindings',len(bindings))
    variants={x['id']:x for x in json.loads(sources['VAR'])['variants']}
    ci={x['id']:x for x in json.loads(sources['CI'])['unknowns']}
    document=j(PKG+'interfaces.json');rows=document['rows'];formulas=j(PKG+'symbolic_dependencies.json')
    must('52_unique_rows',len(rows)==52 and len({r['row_key'] for r in rows})==52 and
         {r['row_key'] for r in rows}=={v+'/'+k for v in variants for k in CONTRACT},'13 specified interfaces per exact variant',len(rows))
    for row in rows:
        rk=row['row_key'];vid,key=rk.split('/');family,option=vid.split('-');v=variants[vid]
        rule,tokens,owners,meaning=CONTRACT[key]
        start=len(checks);unknown='; '.join(x['argument'] for x in row['unknown_arguments'])
        refs=row['source_references'];bindings_selected={b['proposed_cad_field']:b for b in bindings if b['scenario']=='BASE_'+family}
        must(rk+':unknown',row['actual_geometry']=='UNKNOWN' and row['physical_evaluation']=='NOT_RUN' and
             all(x['value'] is None and x['status']=='UNKNOWN' for x in row['unknown_arguments']),
             'unassigned geometry/contact/load arguments',unknown)
        must(rk+':axes_dof_return','+x/+y/+z' in row['node_axes'] and 'UNKNOWN' in row['node_axes']
             and 'UNKNOWN' in row['connection_DOF_contact_sides'] and 'work/return' in row['bidirectional_work_return'],
             'source axes only; actual DOFs/contact sides unknown; bidirectional requirement explicit',row['connection_DOF_contact_sides'])
        must(rk+':source_meaning',all(t.lower() in unknown.lower() for t in tokens),meaning,unknown)
        must(rk+':owners_next',owners<=set(row['functional_data_recipients']) and bool(row['next_check']),
             'functional data owners and future check, no new role claim',{'owners':row['functional_data_recipients'],'next':row['next_check']})
        must(rk+':formula_link',rule is None or rule in row['symbolic_dependency_refs'],'source-supported symbolic component',row['symbolic_dependency_refs'])
        must(rk+':separate_members_full_range',set(row['unresolved_function_symbols'])=={
             'e_y(q)','e_z(q)','L_free_rod(q)','L_free_carrier(q)'},'no scalar/MAX conversion into a known function',row['unresolved_function_symbols'])
        specific=row['variant_specific_conditions'];reaction=row['reaction_phase_conditions']
        must(rk+':variant_semantics',('не нули' in specific if option=='V1' else 'полную силу не делить' in specific),
             'V1 eccentricities unknown; V2 full single-cylinder force',specific)
        must(rk+':reaction_semantics',('startup без столба' in reaction and 'retention/refill' in reaction if family=='A'
             else 'unload/unlock/open/reset' in reaction and 'остаточных' in reaction),
             'A startup/retention or B release/reset require their own evidence',reaction)
        for n,ref in enumerate(refs):
            alias=ref['source'];src=catalog[alias];pid=ref['source_id'];sel=ref['selector']
            okay=ref['commit']==src['commit'] and ref['path']==src['path']
            resolved='document-level read with semantic anchors in row assessment'
            if alias in ('RAW','REG'):
                p=(scoped if alias=='RAW' else original).get(pid)
                okay=okay and p is not None and ref['revision']==p['revision'] and sel=='domains.*.'+pid
                if alias=='RAW':okay=okay and pid.startswith('R3F_'+family+'_'+option+'_') and p['value'] is None
                resolved=p['meaning']
            elif alias=='VAR':
                okay=okay and pid==vid and sel=='variants[id='+vid+']' and ref['revision'] is None
                resolved={'kinematics':v['kinematics'],'force_loop':v['force_loop']}
            elif alias=='BIND':
                field=next((f for f,b in bindings_selected.items() if sel=='rows[scenario=BASE_'+family+',proposed_cad_field='+f+']'),None)
                b=bindings_selected.get(field,{})
                okay=okay and b.get('parameter_id')==pid and b.get('revision')==ref['revision']
                resolved={'field':field,'meaning':original[pid]['meaning'],'source':b.get('source')}
            elif alias=='CI':
                okay=okay and pid in ci and sel=='unknowns[id='+pid+']' and ref['revision'] is None
                resolved=ci[pid]
            else:okay=okay and ref['revision'] is None
            must(rk+':reference:'+str(n),okay,'exact locator and correct ID/revision; no invented revision',{'reference':ref,'resolved':resolved})
        for x in row['source_calculation_references']:
            source=j(x['path'],x['commit']);p=next(a for a in source['inputs']+source['outputs'] if a['id']==x['parameter_id'])
            must(rk+':calc:'+x['parameter_id'],all(x[k]==p[k] for k in ('revision','engineering_sha256')),
                 'source manifest identity, no numerical recalculation',x)
        if key=='datum_motion':
            foreign='CI-X_B_GATHER' if family=='A' else 'CI-X_COLUMN_GATHER'
            present=any(r['source']=='CI' and r['source_id']==foreign for r in refs)
            check(rk+':family_reference_qualified',not present,'row-specific source list should qualify foreign-family gather references',foreign)
            if present:findings.append(dict(id='R5-SYM-OBS-01',row_key=rk,priority='P2',blocking=False,
                source=foreign,observation='Cross-family gather reference exists without an applicability qualifier in this row.',
                impact='Traceability ambiguity only: no force/contact assigned and family-specific conditions remain correct.',
                recipient=['R4','R1'],required_action='Qualify as comparison-only/not applicable, or remove foreign-family reference before machine interpretation of dependencies.'))
        rows_evidence.append(dict(row_key=rk,expected_meaning=meaning,observed_interface=row['interface'],
            source_meanings=[r for r in checks[start:] if ':reference:' in r['id']],
            unknown_arguments=unknown,owners=row['functional_data_recipients'],next_check=row['next_check'],
            checks=[c['id'] for c in checks[start:]],result='WARNING' if key=='datum_motion' else 'PASS',
            physical_validation='NOT_RUN'))
    formula_contract={
        'KIN':('ASSUMED','DOF'), 'AXIAL':('квазистат','guide/channel','не делить'),
        'MOMENT':('обе плоскости','V1','UNKNOWN'), 'GUIDE':('выделенная','не распределение','многоопор'),
        'ROD_NOMINAL':('штока','не сечение носителя','концентраци'),
        'SECTION':('UNKNOWN','I_y/I_z','не выводятся'), 'EULER':('упруг','стройн','плоскост','второй порядок','не вычислены')}
    for name,terms in formula_contract.items():
        f=formulas[name];src=f['source'];text=blob(src['commit'],src['path']).decode()
        must('formula:'+name,all(t.lower() in f['conditions'].lower() for t in terms) and f['expression'] in text and bool(f['missing']),
             'quoted source expression WITH limitations, no evaluation',f)
    states=json.loads(sources['STATE']);mapped=j(PKG+'state_dependencies.json')['rows']
    must('42_exact_states',len(mapped)==42 and [r['source_state'] for r in mapped]==states,'full source state objects and order unchanged',len(mapped))
    state_evidence=[]
    for r in mapped:
        s=r['source_state'];key=s['variant']+'/'+s['state'];text=r['contact_and_load_requirement']
        required={
          'startup_empty':['реакции','нельзя'], 'gather_partial':['partial' if s['variant'].startswith('B') else 'нельзя'],
          'refill':['удерж'], 'hold_unload':['остаточная' if s['variant'].startswith('B') else 'UNKNOWN'],
          'unlock':['низкое давление','не разрешение'], 'stop_open':['остаточная','UNKNOWN'],
          'close_relock_reset':['RESET_CURRENT','не результат'], 'ready':['не следует','NO-GO'],
          'jam_emergency':['авария','не аварийный'], 'work_peak':['F(q,t)','тест'],
          'work_peak_closed':['F(q,t)','тест']}.get(s['state'],['контакт'] if 'return' in s['state'] or 'eject' in s['state'] else ['F(q,t)'])
        must('state:'+key,all(t in text for t in required) and r['actual_solution']=='NOT_RUN' and
             all(r[k] is None for k in ('actual_force','actual_moment','actual_capacity_margin')) and
             s['actual_force_N'] is None and s['actual_moment_Nm'] is None and s['actual_joint_support_loads'] is None and
             s['result']=='UNKNOWN' and set(r['interface_row_keys'])<= {x['row_key'] for x in rows if x['variant']==s['variant']},
             'phase-specific contact evidence only; state NOT solved',text)
        state_evidence.append(dict(state_key=key,expected_qualifiers=required,observed=text,result='PASS',physical_solution='NOT_RUN'))
    index=j(PKG+'unknown_index.json')
    must('unknown_index',len(index)==84 and {x['source']['source_id'] for x in index}==set(raw_ids),
         'index exactly covers 84 preserved RAW records',len(index))
    for x in index:
        pid=x['source']['source_id'];p=raw_ids[pid]
        must('unknown:'+pid,x['value'] is None and x['source_lifecycle']=='RAW' and x['source_unknown_reason']==p['unknown_reason']
             and set(x['interface_rows'])=={r['row_key'] for r in rows if pid in r['source_raw_ids']},
             'RAW meaning and consumers preserved; no known new function/section',x)
    for name in ('interfaces.json','symbolic_dependencies.json','state_dependencies.json','unknown_index.json'):
        nums=[p for p,v in leaves(j(PKG+name)) if type(v) in (int,float)]
        must('no_numeric_assignments:'+name,all(p.endswith('/revision') for p in nums),
             'only inherited revision integers, no assigned engineering numeric leaves',nums)
    for c in checks:
        if c['result']=='FAIL' and not c['id'].endswith(':family_reference_qualified'):
            raise AssertionError(c['id'])
    result=dict(target_C=C,request_H=H,command_C=COMMAND,actual_session_id=SESSION,
        checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        method='Independent immutable-object documentary inspection; no author expected values, physical/numerical calculations or author preflight.',
        counts={k:sum(x['result']==k for x in checks) for k in ('PASS','FAIL')},
        coverage={'interface_rows':len(rows_evidence),'states_compared_not_solved':len(state_evidence),'RAW_null':len(index),
                  'pinned_inputs':len(manifest['inputs']),'protected_trees':len(manifest['protected_trees']),
                  'protected_worktree_files':len(protected),'bindings':len(bindings)},
        checks=checks,row_assessments=rows_evidence,state_assessments=state_evidence,findings=findings,
        verdict='WARNING',input_audit_456='NOT_RUN',physical_READY='NO_GO',G1='OPEN')
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(counts=result['counts'],coverage=result['coverage'],verdict=result['verdict'])))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output)
