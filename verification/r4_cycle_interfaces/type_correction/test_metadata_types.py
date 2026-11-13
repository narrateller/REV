"""Fresh-export type matrices and recovery differential tests, no coercion."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
P = ROOT / 'verification/r4_cycle_interfaces/proposal'
sys.path.insert(0,str(P))
import metadata_types as T
import semantic_minimum as S
import document_semantics as D
sys.path.insert(0,str(P.parent/'correction'))
import test_documentary as prior

PACKET = json.loads((P/'permissions.json').read_text())
POSES = json.loads((P/'poses.json').read_text())
CASES = []
DIFFERENTIAL = []
INVALID = [('true',True),('false',False),('one-float',1.0),('zero-float',0.0),
           ('text','1'),('null',None),('array',[]),('object',{}),('negative',-1),('zero',0)]


def hashes(folder):
    return {str(f.relative_to(folder)):hashlib.sha256(f.read_bytes()).hexdigest()
            for f in folder.rglob('*') if f.is_file() and '__pycache__' not in f.parts}


class RevisionContract(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        target=os.environ.get('REV_TYPES_CAPTURE')
        if target:Path(target).write_text(json.dumps({'cases':CASES,'count':len(CASES),'all_matched':all(c['matched'] for c in CASES),
            'recovery_differential':DIFFERENTIAL,'recovery_count':len(DIFFERENTIAL)},ensure_ascii=False,indent=2)+'\n')

    def exported(self,name,change,after=None,positive=False):
        with tempfile.TemporaryDirectory(prefix='ci-types-') as tmp:
            dest=Path(tmp);pack=dest/'proposal';shutil.copytree(P,pack)
            for f in ['claim.json','input_manifest.json']:shutil.copy(P.parent/f,dest/f)
            change(pack)
            r=subprocess.run([sys.executable,'-B',str(pack/'render_schemes.py'),'--output-dir',str(pack/'exports')],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,(name,r.stderr))
            if after:after(pack)
            before=hashes(pack);manifest=json.loads((pack/'exports/exports_manifest.json').read_text())
            self.assertTrue(all(before[n]==h for n,h in manifest['sources_sha256'].items()))
            self.assertTrue(all(before['exports/'+n]==h for n,h in manifest['exports_sha256'].items()))
            r=subprocess.run([sys.executable,'-B',str(P/'check_package.py'),'--package',str(pack)],capture_output=True,text=True)
            out=json.loads(r.stdout);unchanged=hashes(pack)==before
            matched=(r.returncode==0)==positive and unchanged and (positive or out['verification_gate']=='FAILED')
            CASES.append({'id':name,'expected':'MATCH' if positive else 'NONZERO_REJECTED','observed':out['document_checks'],
                'semantic_outcome':out.get('semantic_outcome'),'exit_code':r.returncode,'matched':matched,
                'fresh_source_export_hashes':True,'checker_writes':not unchanged,'reason':out.get('reason')})
            self.assertTrue(matched,CASES[-1])

    def test_shared_schema_exact_integer_and_quantity_boundary(self):
        for name,v in INVALID:
            self.assertFalse(T.revision(v),name)
            self.assertFalse(T.revision_map({'DOMAIN':v}) if name!='zero' else not T.revision_map({'DOMAIN':v}),name)
        for v in [1,2,2**63]:self.assertTrue(T.revision(v))
        for v in [0,1,2**63]:self.assertTrue(T.revision_map({'DOMAIN':v}))
        for v in [True,1.0,'1',None,[],{}]:self.assertFalse(T.metadata_equal({'x':[1]},{'x':[v]}))
        self.assertFalse(T.metadata_equal({'flag':True},{'flag':1}))
        self.assertTrue(T.quantity_equal(1,1.0))
        self.assertTrue(T.quantity_equal('1/2','1/2'))
        self.assertFalse(T.quantity_equal(True,1.0))
        self.assertTrue(T.metadata_equal({'origin':0,'flag':False},{'origin':0,'flag':False}))

    def test_nested_source_ref_and_metadata_revisions_after_reexport(self):
        locations=[]
        for name in ['A-COMPACT','B-RETURN','A-MECH-WORK','B-MECH-WORK']:
            locations.append(('permissions.json',lambda d,name=name:next(a for a in d['actions'] if a['id']==name)['source_bindings'][0],name+':action-source'))
        for name in ['A-COMPACT','B-RETURN','A-MECH-APPROACH','B-MECH-WORK']:
            locations.append(('permissions.json',lambda d,name=name:next(a for a in d['actions'] if a['id']==name)['resources']['source_main_axis_phase_refs'][0],name+':phase-source'))
            locations.append(('permissions.json',lambda d,name=name:next(a for a in d['actions'] if a['id']==name)['phase_pose_bindings'][0]['stroke_source'],name+':phase-pose-binding'))
        for id,scenario,term in [('P1','BASE_A',1),('P2','BASE_A',2),('P3','BASE_B',3),('P_RETURN_END','BASE_B',4)]:
            def ast_ref(d,id=id,scenario=scenario,term=term):
                node=next(p for p in d['poses'] if p['id']==id)['coordinate_forms'][scenario]['expression']['terms'][term]
                return node.get('operand',node)['source_ref']
            locations.append(('poses.json',ast_ref,id+':'+scenario+':AST'))
        for scenario in ['BASE_A','BASE_B']:
            locations.append(('poses.json',lambda d,scenario=scenario:next(r for r in d['source_refs'] if r['scenario']==scenario),scenario+':pose-source'))
        locations.extend([('permissions.json',lambda d:d['normative_minimum'],'permission-authority'),
                          ('poses.json',lambda d:d['normative_minimum'],'pose-authority'),
                          ('baseline_bindings.json',lambda d:d['rows'][0],'baseline-source')])
        for file,select,tag in locations:
            for name,value in INVALID+[('missing','__MISSING__')]:
                def mutate(pack,file=file,select=select,value=value):
                    p=pack/file;d=json.loads(p.read_text());ref=select(d)
                    if value=='__MISSING__':ref.pop('revision')
                    else:ref['revision']=deepcopy(value)
                    p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
                with self.subTest(location=tag,type=name):self.exported(tag+':'+name,mutate)

    def test_similar_boolean_schema_and_manifest_metadata(self):
        for key,val in [('same_selected_pose',1),('same_selected_pose',0.0),('full_path_obligation',1.0)]:
            def change(pack,key=key,val=val):
                p=pack/'permissions.json';d=json.loads(p.read_text());d['actions'][0]['pose_constraints'][0][key]=val;p.write_text(json.dumps(d))
            self.exported('pose-flag:'+key+':'+str(val),change)
        for val in [True,1.0]:
            def schema(pack,val=val):
                p=pack/'cycle_protocol.json';d=json.loads(p.read_text());d['schema']=val;p.write_text(json.dumps(d))
            self.exported('schema:'+str(val),schema)
            def increment(pack,val=val):
                p=pack/'cycle_protocol.json';d=json.loads(p.read_text());d['fill']['commit_successor']['increment']=val;p.write_text(json.dumps(d))
            self.exported('successor-increment:'+str(val),increment)
            def manifest(pack,val=val):
                p=pack/'exports/exports_manifest.json';d=json.loads(p.read_text());d['normative_minimum']['revision']=val;p.write_text(json.dumps(d))
            self.exported('manifest-revision:'+str(val),lambda p:None,after=manifest)
        for key,val in [('required',1),('wildcards_allowed',0.0)]:
            def change(pack,key=key,val=val):
                p=pack/'permissions.json';d=json.loads(p.read_text());a=next(a for a in d['actions'] if a['id']=='B-MECH-RELOCK');a['recovery_binding']['target_fault_id'][key]=val;p.write_text(json.dumps(d))
            self.exported('recovery-binding-flag:'+key,change)

    def test_positive_integer_refs_and_supported_formula_normalization(self):
        self.exported('positive-original-integer-refs',lambda p:None,positive=True)
        def equivalent(pack):
            p=pack/'poses.json';d=json.loads(p.read_text());r=next(r for r in d['poses'] if r['id']=='P2');r['coordinate']='S_work + (S_approach + x_P0)';p.write_text(json.dumps(d))
        self.exported('positive-equivalent-linear-formula',equivalent,positive=True)

    def test_recovery_origin_types_against_frozen_same_inputs(self):
        def context(start):
            ctx=dict(scenario_id='TYPE-TEST',variant='B',mode='B_REPEAT',state='B_RECEIVED_RESIDUAL',
                subject_id='closure',batch_id='batch',cycle_epoch='epoch',basis_id='basis',basis_revision='r1',
                operation_id='old-denied',revisions={d:start for d in prior.C['evidence_policy']['domains']},
                inventory_refs=['retained'],pending_observations=[])
            ctx=prior.L.initialize_history(ctx,'types-history',dict(value='TRUE',evidence_id='ASSUMED-start',source='synthetic only'))
            ctx=prior.prepare(ctx,'B-NEXT','old-denied');ctx['evidence']['B_RESET_CONFIRMED']['value']='FALSE'
            ctx,_=prior.L.decide(prior.C,'B-NEXT',ctx)
            ctx=prior.prepare(ctx,'RESTORE_B_CLOSURE','new-recovery')
            fault=prior.L.open_faults(ctx,'B_RESET_CONFIRMED')[0]
            proof=prior.evidence(ctx,'RESTORE_B_CLOSURE','B_RESET_CONFIRMED','RECOVERY_RESULT')
            proof.update(fault_id=fault['fault_id'],target_scope=deepcopy(fault['origin']['scope']),
                origin_revisions=deepcopy(fault['origin']['revisions']),revisions=deepcopy(fault['expected_revisions']))
            return ctx,proof
        def compare(name,ctx,proof,expect):
            before=deepcopy((ctx,proof));truth=S.recovery_value(proof,ctx,prior.C)
            returned,outcome=prior.L.recover(prior.C,'RESTORE_B_CLOSURE',ctx,proof['fault_id'],proof)
            self.assertEqual(truth,expect,name)
            self.assertEqual(truth,{'ALLOWED_ASSUMED':'TRUE','BLOCKED':'FALSE','INDETERMINATE':'UNKNOWN'}[outcome],name)
            self.assertEqual((ctx,proof),before)
            self.assertTrue(set(ctx['rejected_operation_ids'])<=set(returned['rejected_operation_ids']))
            self.assertEqual(returned['faults'][proof['fault_id']]['status'],'RESOLVED' if truth=='TRUE' else 'OPEN')
            DIFFERENTIAL.append({'id':name,'predicate':truth,'frozen_outcome':outcome,'original_unchanged':True,
                'returned_fault_status':returned['faults'][proof['fault_id']]['status'],'matched':True})
        for start in [0,1,2**63]:
            ctx,proof=context(start);compare('positive:'+str(start),ctx,proof,'TRUE')
        ctx,proof=context(0)
        bads=INVALID[:-1]+[('wrong-positive',1),('missing','__MISSING__')]
        for field in ['origin_revisions','revisions']:
            for domain in proof[field]:
                for name,value in bads:
                    bad=deepcopy(proof)
                    if value=='__MISSING__':bad[field].pop(domain)
                    else:bad[field][domain]=deepcopy(value)
                    with self.subTest(field=field,domain=domain,value=name):compare(field+':'+domain+':'+name,ctx,bad,'UNKNOWN')
        for domain in proof['origin_revisions']:
            for name,value in INVALID[:-1]:
                bad=deepcopy(ctx);bad['revisions'][domain]=deepcopy(value)
                with self.subTest(domain=domain,current=name):compare('current:'+domain+':'+name,bad,proof,'UNKNOWN')
        for name,val in [('null',None),('foreign','foreign')]:
            bad=deepcopy(proof);bad['target_scope']=val
            compare('target-scope:'+name,ctx,bad,'UNKNOWN')

    def test_fill_successor_metadata_does_not_alias_revisions(self):
        ctx,receipt=prior.FillProtocol().fixture();origin=deepcopy(ctx['revisions'])
        for key in ['material','feed']:ctx['revisions'][key]+=1
        ctx['load_commit']=dict({k:ctx[k] for k in D.FILL_SCOPE},origin_revisions=origin,
            revisions=deepcopy(ctx['revisions']),value='TRUE',boundary='AFTER_DOSER_RETURN',
            receipt_id=receipt['evidence_id'],current_doser='D0',changed_domains=['material','feed'])
        self.assertEqual(D.fill_value(receipt,ctx,True),'TRUE')
        for key,value in [('material',True),('feed',1.0),('history',False),('history',0.0)]:
            bad=deepcopy(ctx);bad['load_commit']['revisions'][key]=value
            self.assertEqual(D.fill_value(receipt,bad,True),'UNKNOWN')


if __name__=='__main__':unittest.main()
