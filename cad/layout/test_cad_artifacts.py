import json,shutil,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from cad_validation import check_cad_adapter,CadValidationError
from layout_common import ROOT,load


class NativeArtifactRegressions(unittest.TestCase):
    def setUp(self):
        self.models=ROOT/'cad/build/research_layout';self.input=ROOT/'cad/layout/conditional_inputs.assumed.json';self.data=load(self.input)
    def test_actual_persisted_models_pass(self):
        r=check_cad_adapter(self.data,self.models,self.input)
        self.assertEqual([r[v]['actual_STEP_shape_correspondence'] for v in 'AB'],['PASS','PASS'])
        self.assertEqual([r[v]['solid_count'] for v in 'AB'],[65,61])
    def test_r5_manifest_only_and_cli_failure_overwrites_old_pass(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            for v in 'AB':
                (root/v).mkdir();shutil.copyfile(self.models/v/'manifest.json',root/v/'manifest.json')
            with self.assertRaises(CadValidationError):check_cad_adapter(self.data,root,self.input)
            out=root/'out';out.mkdir();(out/'report.json').write_text('{"status":"PASS"}')
            cmd=['/usr/bin/python3',str(ROOT/'cad/layout/check_layout.py'),'--inputs',str(self.input),'--models',str(root),'--out',str(out)]
            r=subprocess.run(cmd,text=True,capture_output=True)
            self.assertNotEqual(r.returncode,0);failure=json.loads((out/'report.json').read_text())
            self.assertEqual(failure['status'],'FAILED');self.assertEqual(failure['scenarios'],'NOT_RUN')
    def test_native_process_crash_is_explicit_failure(self):
        with patch('cad_validation.subprocess.run',return_value=SimpleNamespace(returncode=-11,stdout='',stderr='native process failed')):
            with self.assertRaises(CadValidationError) as r:check_cad_adapter(self.data,self.models,self.input)
            self.assertEqual(r.exception.report['status'],'FAILED');self.assertEqual(r.exception.report['exit_code'],-11)


if __name__=='__main__':unittest.main()
