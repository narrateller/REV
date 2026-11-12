"""Small catalog tests; actual FCStd/replay cases are in regress_verifier.py."""
import json,tempfile,unittest
from pathlib import Path
from publication import catalog,digest,write_manifest,verify_manifest,MANIFEST


class PublicationContract(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.artifact=self.root/'cad/build/frame_mount/evidence.json';self.artifact.parent.mkdir(parents=True);self.artifact.write_text('{"geometry":"unchanged"}\n')
        self.manifest=self.root/MANIFEST;write_manifest(self.root)
    def tearDown(self):self.tmp.cleanup()
    def snapshot(self):return {str(p.relative_to(self.root)):(digest(p),p.stat().st_mtime_ns,p.stat().st_size) for p in self.root.rglob('*') if p.is_file()}
    def rejected_without_writes(self):
        before=self.snapshot()
        with self.assertRaises((ValueError,FileNotFoundError,json.JSONDecodeError)):verify_manifest(self.root)
        self.assertEqual(before,self.snapshot())
    def test_two_verifications_identical_and_no_writes(self):
        before=self.snapshot();first=verify_manifest(self.root);second=verify_manifest(self.root)
        self.assertEqual(first,second);self.assertEqual(before,self.snapshot())
    def test_missing_artifact_not_recreated(self):
        self.artifact.unlink();self.rejected_without_writes();self.assertFalse(self.artifact.exists())
    def test_corrupt_artifact_not_repaired(self):
        self.artifact.write_bytes(b'\x00broken');self.rejected_without_writes()
    def test_valid_but_stale_artifact_rejected(self):
        self.artifact.write_text('{"geometry":"previous revision"}\n');self.rejected_without_writes()
    def test_missing_and_stale_manifest_not_regenerated(self):
        self.manifest.unlink();self.rejected_without_writes()
        self.manifest.write_text('{"schema_version":1,"sha256":{}}');self.rejected_without_writes()
    def test_extra_unrecorded_artifact_rejected(self):
        (self.artifact.parent/'extra.json').write_text('{}');self.rejected_without_writes()
    def test_explicit_regeneration_then_repeat_verification(self):
        self.artifact.write_text('{"geometry":"new explicit revision"}\n')
        self.rejected_without_writes();write_manifest(self.root)
        before=self.snapshot();self.assertEqual(verify_manifest(self.root),verify_manifest(self.root));self.assertEqual(before,self.snapshot())


if __name__=='__main__':unittest.main()
