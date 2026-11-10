"""Offline tests for immutable bootstrap, source accounting, handoff and access."""
from contextlib import redirect_stdout
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import operator_console as console


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.template = self.base/'gold'
        # Keep a synthetic TEMPLATE fixture even when CI runs inside a PROJECT.
        shutil.copytree(ROOT/'tests/fixtures/template', self.template)
        for name in ('operator_console.py','init_project.py','check_registry.py',
                     'repository_checks.py','repo_support.py'):
            shutil.copyfile(ROOT/'scripts'/name, self.template/'scripts'/name)
        for name in ('AGENTS.md','AGENT_PROTOCOL.md','NEXT_MODEL.md'):
            shutil.copyfile(ROOT/name, self.template/name)
        self.source = self.base/'materials'; self.source.mkdir()
        (self.source/'brochure.md').write_text('Primary material; see [FICTITIOUS@2] from source.')
        self.project = self.base/'machine'

    def tree_hashes(self, root):
        return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                for p in root.rglob('*') if p.is_file()}

    def create(self, with_sources=True):
        with redirect_stdout(io.StringIO()):
            return console.create_project(self.template, self.project, 'MACHINE-1',
                                          'Произвольное оборудование', 'Оператор',
                                          self.source if with_sources else None)

    def git(self, *args):
        return subprocess.run(['git','-C',str(self.project),*args],capture_output=True,text=True,check=True).stdout.strip()

    def init_git(self):
        self.git('init','-q')
        self.git('config','user.name','TEST FIXTURE')
        self.git('config','user.email','tests@example.invalid')
        self.git('add','.');self.git('commit','-qm','test baseline')
        return self.git('rev-parse','HEAD')

    def test_gold_unchanged_and_sources_checked(self):
        before=self.tree_hashes(self.template);self.create()
        self.assertEqual(before,self.tree_hashes(self.template))
        problems,manifest=console.local_checks(self.project)
        self.assertEqual(problems,[]);self.assertEqual(manifest['sources_status'],'PRESENT_UNREVIEWED')
        self.assertEqual(len(manifest['sources']),1)
        self.assertTrue((self.project/'NEXT_MODEL.md').exists())
        self.assertTrue((self.project/'project/access_challenge.txt').exists())

    def test_message_for_attached_and_unattached_context(self):
        self.assertEqual(console.next_message(),'Войди в курс дел и текущий статус проекта.')
        self.assertIn('https://github.com/another-owner/project',console.next_message('another-owner/project','work/T1'))
        with self.assertRaises(ValueError):console.next_message('bad/repo\ninjection')

    def test_interactive_prepare(self):
        answers='1\n'+str(self.project)+'\nMACHINE-1\nУниверсальный агрегат\nОператор\n'+str(self.source)+'\n'
        result=subprocess.run([sys.executable,str(self.template/'scripts/operator_console.py')],
                              input=answers,text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('Проект подготовлен',result.stdout)
        self.assertTrue((self.project/'NEXT_MODEL.md').exists())

    def test_missing_handoff_detected(self):
        self.create();(self.project/'NEXT_MODEL.md').unlink()
        self.assertTrue(any('NEXT_MODEL.md' in e for e in console.local_checks(self.project)[0]))

    def test_challenges_are_per_project(self):
        self.create(); other=self.base/'second'
        with redirect_stdout(io.StringIO()):
            console.create_project(self.template,other,'MACHINE-2','Другой объект','Оператор',self.source)
        self.assertNotEqual((self.project/'project/access_challenge.txt').read_text(),
                            (other/'project/access_challenge.txt').read_text())

    def test_no_sources_then_add(self):
        self.create(False);self.assertTrue(console.local_checks(self.project)[0])
        with redirect_stdout(io.StringIO()):console.add_sources(self.project,self.source)
        self.assertEqual(console.local_checks(self.project)[0],[])

    def test_source_duplicate_does_not_overwrite(self):
        self.create();target=self.project/'sources/raw/brochure.md';before=target.read_bytes()
        (self.source/'brochure.md').write_text('Changed')
        with self.assertRaises(FileExistsError):console.add_sources(self.project,self.source)
        self.assertEqual(target.read_bytes(),before)

    def test_changed_source_detected(self):
        self.create();(self.project/'sources/raw/brochure.md').write_text('Changed')
        self.assertTrue(any('CHANGED' in e for e in console.local_checks(self.project)[0]))

    def test_unregistered_source_detected(self):
        self.create();(self.project/'sources/raw/extra.txt').write_text('Unregistered')
        self.assertTrue(any('UNREGISTERED' in e for e in console.local_checks(self.project)[0]))

    def test_no_overwrite_or_nested_project(self):
        self.create()
        with self.assertRaises(FileExistsError):self.create()
        with self.assertRaises(ValueError):
            console.create_project(self.template,self.template/'nested','MACHINE-2','Test','Operator')
        with self.assertRaises(ValueError):
            console.create_project(self.template,self.base,'MACHINE-2','Test','Operator')

    def test_symlink_source_refused(self):
        (self.source/'link').symlink_to(self.source/'brochure.md')
        with self.assertRaises(ValueError):self.create()
        self.assertFalse(self.project.exists())

    def test_add_sources_symlink_destination_refused(self):
        self.create(False)
        outside=self.base/'outside';outside.mkdir()
        (self.project/'sources/raw/link').symlink_to(outside,target_is_directory=True)
        (self.source/'link').mkdir();(self.source/'link/new.txt').write_text('test')
        with self.assertRaises(FileExistsError):console.add_sources(self.project,self.source)
        self.assertFalse((outside/'new.txt').exists())

    def test_read_access_receipt_matches_git_commit(self):
        self.create();commit=self.init_git();challenge=(self.project/'project/access_challenge.txt').read_text().strip()
        with redirect_stdout(io.StringIO()):console.record_access(self.project,'TEST MODEL','TEST_SESSION',commit,challenge)
        data=json.loads((self.project/'project/access_receipts/TEST_SESSION.json').read_text())
        self.assertEqual(data['read_status'],'OPERATOR_REPORTED_RESPONSE_MATCHED_GIT')
        self.assertEqual(data['write_status'],'NOT_VERIFIED')
        with self.assertRaises(FileExistsError):console.record_access(self.project,'TEST MODEL','TEST_SESSION',commit,challenge)

    def test_wrong_challenge_and_commit_refused(self):
        self.create();commit=self.init_git();challenge=(self.project/'project/access_challenge.txt').read_text().strip()
        with self.assertRaises(ValueError):console.record_access(self.project,'TEST','S1',commit,'incorrect')
        with self.assertRaises(ValueError):console.record_access(self.project,'TEST','S1','0'*40,challenge)
        self.assertFalse((self.project/'project/access_receipts/S1.json').exists())

    def test_write_probe_only_remote_tracking_ref(self):
        self.create();commit=self.init_git();challenge=(self.project/'project/access_challenge.txt').read_text().strip()
        path=self.project/'project/access_probes/S2.md';path.parent.mkdir();path.write_text(challenge+'\n')
        self.git('add',str(path.relative_to(self.project)));self.git('commit','-qm','test probe')
        tip=self.git('rev-parse','HEAD');self.git('update-ref','refs/remotes/origin/access/S2',tip)
        with redirect_stdout(io.StringIO()):
            console.record_access(self.project,'TEST','S2',commit,challenge,'refs/remotes/origin/access/S2')
        data=json.loads((self.project/'project/access_receipts/S2.json').read_text())
        self.assertEqual(data['write_status'],'REMOTE_TRACKING_REF_OBSERVED_LOCALLY')

    def test_probe_wrong_ref_refused(self):
        self.create();commit=self.init_git();challenge=(self.project/'project/access_challenge.txt').read_text().strip()
        with self.assertRaises(ValueError):console.record_access(self.project,'TEST','S3',commit,challenge,'refs/heads/main')

    def test_unknown_remote_does_not_imply_access(self):
        self.create()
        actual_run=subprocess.run
        with patch.object(console,'gh_identity',return_value='operator'), patch.object(console.subprocess,'run') as run:
            def fake(args,**kwargs):
                if args[0]=='gh':return subprocess.CompletedProcess(args,1,'','not accessible')
                return actual_run(args,**kwargs)
            run.side_effect=fake
            with redirect_stdout(io.StringIO()) as out: result=console.doctor(self.project,'owner/repo')
        self.assertEqual(result,1);self.assertIn('UNKNOWN',out.getvalue())

    def test_publish_wrong_account_stops_before_mutation(self):
        self.create()
        with patch.object(console,'gh_identity',return_value='actual'):
            with self.assertRaises(RuntimeError):
                console.publish(self.project,'owner/repo','private','other','CREATE owner/repo')
        self.assertFalse((self.project/'.git').exists())

    def test_publish_requires_exact_confirmation(self):
        self.create()
        with self.assertRaises(ValueError):console.publish(self.project,'owner/repo','private','owner','yes')
        self.assertFalse((self.project/'.git').exists())

    def test_publish_constructs_gh_command_in_offline_mock(self):
        self.create(); calls=[]
        def fake(args, **kwargs):
            calls.append(args);return subprocess.CompletedProcess(args,0,'','')
        with patch.object(console,'gh_identity',return_value='actual'), patch.object(console,'local_checks',return_value=([],{})), \
             patch.object(console.shutil,'which',return_value='/test/tool'), patch.object(console.subprocess,'run',side_effect=fake), \
             redirect_stdout(io.StringIO()):
            console.publish(self.project,'other-account/project','private','actual','CREATE other-account/project')
        self.assertEqual(calls[-1][:5],['gh','repo','create','other-account/project','--private'])
        self.assertIn('--push',calls[-1]);self.assertIn('--source',calls[-1])


if __name__=='__main__':unittest.main()
