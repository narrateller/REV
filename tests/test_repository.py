"""Synthetic test fixtures only; no real engineering approvals are created."""
from contextlib import redirect_stdout
import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import check_registry as checker
import init_project as initializer
from repo_support import engineering_sha, flatten, parameter_ref, sha256, valid_tolerance


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/'repo'
        shutil.copytree(ROOT/'tests/fixtures/template', self.root)
        for filename in ('check_registry.py','repository_checks.py','repo_support.py','init_project.py'):
            shutil.copyfile(ROOT/'scripts'/filename, self.root/'scripts'/filename)
        subprocess.run([sys.executable, str(self.root/'scripts/demo_force.py'), '--write'],
                       check=True, capture_output=True)
        self.data = yaml.load((self.root/'params/registry.yaml').read_text(), Loader=checker.UniqueLoader)

    def p(self, key='DEMO_CONTACT_AREA'):
        return flatten(self.data)[key]

    def save(self):
        (self.root/'params/registry.yaml').write_text(yaml.safe_dump(self.data, allow_unicode=True, sort_keys=False))

    def errors(self, **kwargs):
        self.save()
        return checker.validate(self.data, self.root, **kwargs)

    def rejects(self, text, **kwargs):
        errors = self.errors(**kwargs)
        self.assertTrue(any(text.lower() in x.lower() for x in errors), (text, errors))

    def manifest(self, change):
        path = self.root/'evidence/demo_force.json'
        data = json.loads(path.read_text()); change(data)
        path.write_text(json.dumps(data))

    def verified(self, commit='a'*40):
        p = self.p()
        p['lifecycle'] = 'VERIFIED'
        p['history'].append({'revision':p['revision'], 'to':'VERIFIED'})
        p['evidence'] = ['evidence/demo_force.json']
        p['verifier'] = {'role':'R5','session_id':'TEST_REVIEWER','review_id':'REV-TEST','scope':'ARITHMETIC_ONLY'}
        record = {'record_type':'review','review_id':'REV-TEST', 'reviewer':{'role':'R5','session_id':'TEST_REVIEWER'},
                  'author_sessions':['TEMPLATE_AUTHOR'], 'independence_basis':'Synthetic unit-test fixture',
                  'reviewed_commit':commit, 'scope':'ARITHMETIC_ONLY',
                  'parameter_refs':[parameter_ref('DEMO_CONTACT_AREA',p)],
                  'artifacts':[{'path':'evidence/demo_force.json','sha256':sha256(self.root/'evidence/demo_force.json')}],
                  'checks':[{'method':'synthetic_test','expected':'fixture expected','observed':'fixture observed',
                             'reasoning':'TEST ONLY','result':'PASS'}], 'verdict':'PASS','validity':'CURRENT'}
        self.write_review(record)
        return record

    def write_review(self, record):
        (self.root/'reviews/cross_check_log.md').write_text('# TEST ONLY\n\n```yaml\n'+yaml.safe_dump(record)+'```\n')

    def init(self, **kwargs):
        with redirect_stdout(io.StringIO()):
            initializer.init_project(self.root, 'TEST-PROJECT', 'Test equipment', 'Operator', **kwargs)

    def test_valid_template(self): self.assertEqual(self.errors(), [])
    def test_tolerances(self):
        for tol in ({'kind':'absolute','minus':0,'plus':1},
                    {'kind':'relative_percent','minus':5,'plus':120},
                    {'kind':'min_only','min':1.5}, {'kind':'max_only','max':-1},
                    {'kind':'fit','designation':'H7/g6','standard_ref':'TEST STANDARD',
                     'nominal_ref':'[NOMINAL@1]','limits_refs':['[LOWER@1]','[UPPER@1]']}):
            with self.subTest(tol=tol): self.assertTrue(valid_tolerance(tol, 2))
    def test_invalid_tolerances(self):
        for tol in ({'kind':'min_only','min':True}, {'kind':'max_only','max':float('nan')},
                    {'kind':'relative_percent','minus':0,'plus':float('inf')},
                    {'kind':'absolute','minus':-1,'plus':0}, {'kind':'fit','designation':'H7'},
                    {'kind':'min_only','min':1,'extra':0}):
            with self.subTest(tol=tol): self.assertFalse(valid_tolerance(tol, 2))
        self.assertFalse(valid_tolerance({'kind':'relative_percent','minus':1,'plus':1},0))
    def test_duplicate_yaml(self):
        with self.assertRaises(ValueError): yaml.load('a: 1\na: 2', Loader=checker.UniqueLoader)
    def test_nonfinite_value(self): self.p()['value']=float('nan'); self.rejects('finite')
    def test_missing_unknown_reason(self):
        self.p('DEMO_REF_THROUGHPUT')['unknown_reason']=None; self.rejects('unknown without reason')
    def test_dependency_cycle(self):
        self.p('DEMO_CONTACT_STRESS')['depends_on']=[{'id':'DEMO_REQUIRED_FORCE','revision':1}]
        self.rejects('cycle')
    def test_changed_revision(self): self.p()['revision']=2; self.rejects('outdated dependency')
    def test_changed_input_without_revision(self): self.p()['value']=0.007; self.rejects('changed parameter')
    def test_hash_script(self):
        with (self.root/'scripts/demo_force.py').open('a') as f:f.write('\n# changed\n')
        self.rejects('script_sha256 mismatch')
    def test_hash_local_module(self):
        with (self.root/'scripts/repo_support.py').open('a') as f:f.write('\n# changed\n')
        self.rejects('artifact hash mismatch')
    def test_hash_registry_snapshot(self):
        ev=json.loads((self.root/'evidence/demo_force.json').read_text())
        with (self.root/ev['registry_snapshot']).open('a') as f:f.write('\n# changed\n')
        self.rejects('registry_sha256 mismatch')
    def test_missing_script_hash(self): self.manifest(lambda x:x.pop('script_sha256')); self.rejects('script_sha256 required')
    def test_wrong_output_value(self): self.manifest(lambda x:x['outputs'][0].update(value=0)); self.rejects('value/unit mismatch')
    def test_missing_input(self): self.manifest(lambda x:x.update(inputs=[])); self.rejects('dependency set mismatch')
    def test_duplicate_json(self):
        path=self.root/'evidence/demo_force.json'; path.write_text('{"x":1,"x":2}')
        self.rejects('duplicate json')
    def test_lfs_pointer(self):
        (self.root/'evidence/demo_force.json').write_text('version https://git-lfs.github.com/spec/v1\noid sha256:'+'0'*64+'\nsize 1\n')
        self.rejects('LFS object not materialized')
    def test_lfs_pointer_crlf(self):
        (self.root/'evidence/demo_force.json').write_bytes(
            b'version https://git-lfs.github.com/spec/v1\r\noid sha256:' + b'0'*64 + b'\r\nsize 1\r\n')
        self.rejects('LFS object not materialized')

    def test_git_hash_preserves_crlf_evidence(self):
        # Emulate Windows CRLF with core.autocrlf enabled; repository attributes
        # must preserve the exact evidence bytes used for SHA256.
        subprocess.run(['git','-C',str(self.root),'init','-q'],check=True,capture_output=True)
        for key,value in (('user.email','tests@example.invalid'),('user.name','TEST FIXTURE'),('core.autocrlf','true')):
            subprocess.run(['git','-C',str(self.root),'config',key,value],check=True,capture_output=True)
        evidence=self.root/'evidence/demo_force.json'
        evidence.write_bytes(evidence.read_bytes().replace(b'\n',b'\r\n'))
        subprocess.run(['git','-C',str(self.root),'add','.'],check=True,capture_output=True)
        subprocess.run(['git','-C',str(self.root),'commit','-qm','CRLF test baseline'],check=True,capture_output=True)
        commit=subprocess.check_output(['git','-C',str(self.root),'rev-parse','HEAD'],text=True).strip()
        blob=subprocess.check_output(['git','-C',str(self.root),'show',commit+':evidence/demo_force.json'])
        self.assertEqual(blob,evidence.read_bytes())
        self.verified(commit)
        self.assertEqual(self.errors(check_git=True),[])

    def test_git_review_materialized_lfs_artifact(self):
        subprocess.run(['git','-C',str(self.root),'init','-q'],check=True,capture_output=True)
        for key,value in (('user.email','tests@example.invalid'),('user.name','TEST FIXTURE')):
            subprocess.run(['git','-C',str(self.root),'config',key,value],check=True,capture_output=True)
        payload=b'synthetic binary artifact for test only\x00\x01'
        (self.root/'artifact.dat').write_bytes(payload)
        subprocess.run(['git','-C',str(self.root),'add','.'],check=True,capture_output=True)
        digest=hashlib.sha256(payload).hexdigest()
        pointer=('version https://git-lfs.github.com/spec/v1\n'
                 f'oid sha256:{digest}\nsize {len(payload)}\n').encode()
        blob=subprocess.run(['git','-C',str(self.root),'hash-object','-w','--stdin'],input=pointer,
                            capture_output=True,check=True).stdout.decode().strip()
        subprocess.run(['git','-C',str(self.root),'update-index','--add','--cacheinfo',
                        f'100644,{blob},artifact.dat'],check=True,capture_output=True)
        subprocess.run(['git','-C',str(self.root),'commit','-qm','LFS pointer fixture'],check=True,capture_output=True)
        commit=subprocess.check_output(['git','-C',str(self.root),'rev-parse','HEAD'],text=True).strip()
        record=self.verified(commit)
        record['artifacts'].append({'path':'artifact.dat','sha256':digest})
        self.write_review(record)
        self.assertEqual(self.errors(check_git=True),[])
    def test_unknown_markdown_ref(self):
        (self.root/'requirements.md').write_text('[NO_PARAMETER@1]'); self.rejects('unknown parameter reference')
    def test_outdated_markdown_ref(self):
        (self.root/'requirements.md').write_text('[DEMO_CONTACT_AREA@2]'); self.rejects('outdated markdown')
    def test_stale_markdown_ref(self):
        p=self.p('DEMO_YIELD_SAFETY_FACTOR');p.update(validity='STALE',stale_reason='test')
        (self.root/'requirements.md').write_text('[DEMO_YIELD_SAFETY_FACTOR@1]');self.rejects('stale markdown')
    def test_archive_refs_excluded(self):
        (self.root/'archive').mkdir(); (self.root/'archive/old.md').write_text('[OLD@1]')
        self.assertEqual(self.errors(),[])
    def test_stale_dev_vs_strict(self):
        self.p('DEMO_YIELD_SAFETY_FACTOR').update(validity='STALE',stale_reason='test')
        self.assertEqual(self.errors(),[]); self.rejects('STALE forbidden',strict=True)
    def test_valid_verification_no_recalculation(self):
        self.verified(); self.assertEqual(self.errors(),[])
    def test_fake_review_substring(self):
        self.verified();(self.root/'reviews/cross_check_log.md').write_text('REV-TEST and REV-TEST-OTHER are just text')
        self.rejects('exact review_id not found')
    def test_review_warning(self):
        r=self.verified();r['verdict']='WARNING';self.write_review(r);self.rejects('requires PASS')
    def test_review_stale(self):
        r=self.verified();r['validity']='STALE';self.write_review(r);self.rejects('STALE verification')
    def test_self_verification_coauthor(self):
        self.verified();self.p()['author_sessions'].append('TEST_REVIEWER');self.rejects('coauthor')
    def test_review_wrong_parameter(self):
        r=self.verified();r['parameter_refs']=[parameter_ref('DEMO_YIELD_SAFETY_FACTOR',self.p('DEMO_YIELD_SAFETY_FACTOR'))]
        self.write_review(r);self.rejects('does not cover')
    def test_review_missing_evidence_coverage(self):
        r=self.verified();r['artifacts']=[{'path':'README.md','sha256':sha256(self.root/'README.md')}]
        self.write_review(r);self.rejects('does not cover parameter evidence')
    def test_review_duplicate_id(self):
        self.verified();p=self.root/'reviews/cross_check_log.md';p.write_text(p.read_text()*2);self.rejects('duplicate review_id')
    def test_review_not_run(self):
        r=self.verified();r['checks'][0]['result']='NOT_RUN';self.write_review(r);self.rejects('failed/unrun')
    def test_git_missing_commit(self): self.verified();self.rejects('Git object unavailable',check_git=True)
    def test_git_review_positive(self):
        for args in (['init','-q'],['config','user.email','tests@example.invalid'],['config','user.name','TEST FIXTURE'],['add','.'],['commit','-qm','test baseline']):
            subprocess.run(['git','-C',str(self.root)]+args, check=True,capture_output=True)
        commit=subprocess.check_output(['git','-C',str(self.root),'rev-parse','HEAD'],text=True).strip()
        self.verified(commit);self.assertEqual(self.errors(check_git=True),[])
    def test_lock_requires_real_decision_record(self):
        self.verified();p=self.p();p.update(lifecycle='LOCKED',baseline_id='DEC-TEST');p['history'].append({'revision':1,'to':'LOCKED'})
        (self.root/'decisions').mkdir();(self.root/'decisions/DEC-TEST.md').write_text('APPROVED DEC-TEST')
        self.rejects('Exactly one decision')
    def test_lock_positive_and_rejected(self):
        r=self.verified();p=self.p();p.update(lifecycle='LOCKED',baseline_id='DEC-TEST');p['history'].append({'revision':1,'to':'LOCKED'})
        d={'record_type':'decision','decision_id':'DEC-TEST','gate':'G1','status':'APPROVED',
           'approved_by':'TEST ONLY','approver_kind':'HUMAN','authorization_evidence':'Synthetic fixture, not real approval',
           'approved_at_utc':'2026-11-09T00:00:00Z','baseline_commit':'a'*40,'scope':'TEST',
           'parameter_refs':[parameter_ref('DEMO_CONTACT_AREA',p)],'review_ids':['REV-TEST'],
           'artifacts':r['artifacts'],'blocking_issues_remaining':[]}
        (self.root/'decisions').mkdir();path=self.root/'decisions/DEC-TEST.md'
        path.write_text('```yaml\n'+yaml.safe_dump(d)+'```\n');self.assertEqual(self.errors(),[])
        d['status']='REJECTED';path.write_text('```yaml\n'+yaml.safe_dump(d)+'```\n');self.rejects('APPROVED without blockers')
    def test_project_rejects_demo(self):
        self.data.update(mode='PROJECT',project_id='TEST');self.rejects('DEMO forbidden')
    def test_cots_candidate(self):
        c={'schema_version':'1.1','components':{'COTS_TEST':{'status':'CANDIDATE','owner_role':'R3','interface_parameters':{},'rating_parameters':{}}}}
        (self.root/'drives/cots_catalog.yaml').write_text(yaml.safe_dump(c));self.assertEqual(self.errors(),[])
    def test_cots_approval_incomplete(self):
        c={'schema_version':'1.1','components':{'COTS_TEST':{'status':'APPROVED_FOR_LAYOUT','owner_role':'R3','interface_parameters':{},'rating_parameters':{}}}}
        (self.root/'drives/cots_catalog.yaml').write_text(yaml.safe_dump(c));self.rejects('missing manufacturer')
    def test_cots_approved_and_source_tampering(self):
        source=self.root/'catalog.txt';source.write_text('SYNTHETIC CATALOG FOR TEST ONLY')
        p=copy.deepcopy(self.p());p.update(scope='PROJECT',lifecycle='VERIFIED',evidence=['catalog.txt'])
        p['history'].append({'revision':1,'to':'VERIFIED'})
        p['verifier']={'role':'R5','session_id':'TEST_REVIEWER','review_id':'REV-COTS','scope':'CATALOG_CHECK'}
        self.data['domains']['geometry_mass']['TEST_INTERFACE']=p
        record={'record_type':'review','review_id':'REV-COTS','reviewer':{'role':'R5','session_id':'TEST_REVIEWER'},
                'author_sessions':['TEMPLATE_AUTHOR'],'independence_basis':'TEST FIXTURE','reviewed_commit':'a'*40,
                'scope':'CATALOG_CHECK','parameter_refs':[parameter_ref('TEST_INTERFACE',p)],
                'artifacts':[{'path':'catalog.txt','sha256':sha256(source)}],
                'checks':[{'method':'test','expected':'test','observed':'test','reasoning':'TEST ONLY','result':'PASS'}],
                'verdict':'PASS','validity':'CURRENT'}
        self.write_review(record)
        c={'status':'APPROVED_FOR_LAYOUT','owner_role':'R3','manufacturer':'TEST','model':'TEST',
           'variant':'TEST','catalog_revision':'TEST','source_locator':'TEST PAGE','coordinate_system':'TEST AXES',
           'source_file':'catalog.txt','source_sha256':sha256(source),'required_interfaces':['mount'],
           'interface_parameters':{'mount':'[TEST_INTERFACE@1]'},'rating_parameters':{},
           'unresolved_items':[],'review_id':'REV-COTS'}
        (self.root/'drives/cots_catalog.yaml').write_text(yaml.safe_dump({'schema_version':'1.1','components':{'COTS_TEST':c}}))
        self.assertEqual(self.errors(),[])
        source.write_text('TAMPERED TEST CATALOG');self.rejects('hash mismatch')
    def test_init_dry_run(self):
        before=(self.root/'params/registry.yaml').read_bytes();self.init(dry_run=True)
        self.assertEqual(before,(self.root/'params/registry.yaml').read_bytes());self.assertFalse((self.root/'.init_project_backup').exists())
    def test_init_success_preserves_sources(self):
        src=self.root/'sources/raw';src.mkdir(parents=True);(src/'user.txt').write_text('Keep this source')
        self.init();data=yaml.safe_load((self.root/'params/registry.yaml').read_text())
        self.assertEqual(data['mode'],'PROJECT');self.assertFalse(flatten(data))
        self.assertEqual(checker.validate(data,self.root),[])
        self.assertEqual((src/'user.txt').read_text(),'Keep this source')
        self.assertTrue((self.root/'examples/template_demo/params/registry.yaml').exists())
    def test_init_repeat_refused(self):
        self.init();before=(self.root/'params/registry.yaml').read_bytes()
        with self.assertRaises(ValueError):self.init()
        self.assertEqual(before,(self.root/'params/registry.yaml').read_bytes())
    def test_init_project_data_refused(self):
        self.data['domains']['geometry_mass']['PROJECT_AREA']=copy.deepcopy(self.p());self.save()
        with self.assertRaises(ValueError):self.init()
    def test_init_changed_state_refused(self):
        path=self.root/'STATE.md';path.write_text(path.read_text().replace('UNSET / UNKNOWN','CHANGED'))
        with self.assertRaises(ValueError):self.init()
    def test_init_rollback_on_write_failure(self):
        original=initializer.atomic_write;calls=[]
        before={p:(self.root/p).read_bytes() for p in ('params/registry.yaml','STATE.md','scripts/demo_force.py')}
        def fail_once(path, content):
            calls.append(path)
            if len(calls)==2:raise OSError('Injected write failure')
            return original(path, content)
        with patch.object(initializer,'atomic_write',side_effect=fail_once):
            with self.assertRaises(OSError):self.init()
        for p,value in before.items():self.assertEqual((self.root/p).read_bytes(),value)
    def test_init_lock_refused(self):
        (self.root/'.init_project.lock').write_text('Other initializer')
        with self.assertRaises(FileExistsError):self.init()
        self.assertTrue((self.root/'.init_project.lock').exists())
    def test_init_invalid_user_input(self):
        with self.assertRaises(ValueError):initializer.init_project(self.root,'../BAD','Test','Owner')
    def test_init_external_target_refused(self):
        outside=Path(self.temp.name)/'outside';outside.mkdir()
        (self.root/'examples').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):self.init()
        self.assertEqual(list(outside.iterdir()),[])


if __name__=='__main__': unittest.main()
