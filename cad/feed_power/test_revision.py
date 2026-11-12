import copy,tempfile,unittest
from unittest.mock import patch
import common as c


class GeometryRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=c.load(c.INPUT)
    def test_all_old_IDs_and_work_strokes_retained(self):
        old=c.load(c.ROOT/'cad/frame_mount/inputs.assumed.json')
        for v in 'AB':self.assertTrue({x['id'] for x in c.selected(old,v)} <= {x['id'] for x in c.selected(self.data,v)})
        for k,r in old['config'].items():self.assertEqual(self.data['parameters'][r],old['parameters'][r])
        self.assertEqual(c.checked.bodies(old,'A')['doser_slide'],c.checked.bodies(self.data,'A')['doser_slide'])
    def test_old_UP_is_blocked_new_side_lift_does_not_intersect_hopper(self):
        initial=c.checked.bodies(self.data,'A');old=copy.deepcopy(initial);old['doser_slide']['delta']=['0','0',str(c.config(self.data,'service_lift'))]
        for a,b in c.LEGACY:self.assertEqual(c.strict_interval(old[a],old[b])['status'],'POSITIVE_BOUND_OVERLAP')
        current=initial
        for move in c.plans(self.data)['doser_retract_lift']:
            state=copy.deepcopy(current)
            for n,d in move:state[n]['delta']=list(map(str,d))
            for a,b in c.LEGACY:self.assertEqual(c.strict_interval(state[a],state[b])['status'],'NO_POSITIVE_VOLUME_ON_INTERVAL')
            current=c.checked.advance(state)
        self.assertEqual(current,initial)
    def test_service_plans_restore_every_moved_body(self):
        for label,plan in c.plans(self.data).items():
            total={}
            for move in plan:
                for n,d in move:total[n]=[a+b for a,b in zip(total.get(n,[c.F(0)]*3),d)]
            self.assertTrue(all(all(x==0 for x in d) for d in total.values()),label)
        self.assertEqual([move[0][1][2] for move in c.plans(self.data)['motor']],[c.config(self.data,'service_lift'),-c.config(self.data,'service_lift')])
    def test_original_cap_UP_corridor_not_blocked_by_new_parts(self):
        s=c.checked.bodies(self.data,'A');s['gate_service_cap']['delta']=['0','0',str(c.config(self.data,'service_cap_z'))]
        names=set(x['id'] for x in self.data['components'])-set(x['id'] for x in c.load(c.ROOT/'cad/frame_mount/inputs.assumed.json')['components'])
        for n in names:self.assertEqual(c.strict_interval(s['gate_service_cap'],s[n])['status'],'NO_POSITIVE_VOLUME_ON_INTERVAL',n)


class ReadonlyCatalogRegression(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();root=c.Path(self.temp.name);out=root/'cad/build/feed_power';audit=root/'verification/r4_feed_power';out.mkdir(parents=True);audit.mkdir(parents=True);(root/'cad/feed_power').mkdir()
        for n in ('input_audit.md','input_manifest.json','before_inventory.json','frozen_tool.json'):(audit/n).write_text('{}')
        self.artifact=out/'part.FCStd';self.artifact.write_bytes(b'fixture');self.manifest=out/'publication_manifest.json';self.patch=patch.multiple(c,ROOT=root,OUT=out,AUDIT=audit);self.patch.start();c.seal()
    def tearDown(self):self.patch.stop();self.temp.cleanup()
    def snapshot(self):return {str(p):(c.digest(p),p.stat().st_mtime_ns) for p in c.Path(self.temp.name).rglob('*') if p.is_file()}
    def test_two_verifies_do_not_write(self):
        before=self.snapshot();self.assertEqual(c.verify_manifest(),c.verify_manifest());self.assertEqual(before,self.snapshot())
    def test_missing_and_corrupt_artifact_fail_without_repair(self):
        for value in (None,b'bad'):
            if value is None:self.artifact.unlink()
            else:self.artifact.write_bytes(value)
            before=self.snapshot()
            with self.assertRaises(ValueError):c.verify_manifest()
            self.assertEqual(before,self.snapshot())
    def test_missing_manifest_not_regenerated(self):
        self.manifest.unlink();before=self.snapshot()
        with self.assertRaises(FileNotFoundError):c.verify_manifest()
        self.assertEqual(before,self.snapshot())


if __name__=='__main__':unittest.main()
