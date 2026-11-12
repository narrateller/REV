import copy,json,tempfile,unittest
from pathlib import Path
from layout_common import load
from check_layout import evaluate_pair,assess_continuity,continuity_status,advance

def box(lo,hi,d=(0,0,0),exact=True):return {'lo':[str(x) for x in lo],'hi':[str(x) for x in hi],'delta':[str(x) for x in d],'motion':'linear','exact_box':exact,'group':'test','rigid_group':'test'}
class AdapterChecks(unittest.TestCase):
 def test_missing_value_blocks_build(self):
  p=Path(__file__).with_name('conditional_inputs.assumed.json');data=json.loads(p.read_text());next(iter(data['parameters'].values()))['value']=None
  with tempfile.TemporaryDirectory() as tmp:
   q=Path(tmp)/'input.json';q.write_text(json.dumps(data))
   with self.assertRaises(ValueError):load(q)
 def test_curve_overlap_is_unknown_not_box_collision(self):
  a=box([0,0,0],[1,1,1],exact=False);b=box([0,0,0],[1,1,1])
  self.assertEqual(evaluate_pair(a,b,'barrel','frame',['0','1'],'A')['status'],'INDETERMINATE')
  b=box([3,0,0],[4,1,1]);self.assertEqual(evaluate_pair(a,b,'barrel','frame',['0','1'],'A')['status'],'CLEAR')
 def test_midinterval_collision(self):
  a=box([-3,0,0],[-2,1,1],[6,0,0]);b=box([0,0,0],[1,1,1]);r=evaluate_pair(a,b,'punch','wall',['0','1'],'A')
  self.assertEqual(r['status'],'COLLISION');self.assertEqual(r['evidence']['segments'][0]['collision_status'],'CLEAR');self.assertEqual(r['evidence']['segments'][-1]['collision_status'],'CLEAR')
 def test_product_link_and_unknown(self):
  a=box([-1,0,0],[0,1,1],[2,0,0]);b=box([0,0,0],[1,1,1],[2,0,0]);r=evaluate_pair(a,b,'punch','product_A',['0','1'],'A')
  self.assertEqual(r['evidence']['link'],'LINK_CONFIRMED');b['delta']=None;self.assertEqual(evaluate_pair(a,b,'punch','product_A',['0','1'],'A')['status'],'INDETERMINATE')
 def test_return_intermediate_collision(self):
  a=box([3,0,0],[4,1,1],[-6,0,0]);b=box([0,0,0],[1,1,1]);r=evaluate_pair(a,b,'punch','wall',['0','1'],'B')
  self.assertEqual(r['status'],'COLLISION');self.assertEqual(r['evidence']['segments'][0]['collision_status'],'CLEAR');self.assertEqual(r['evidence']['segments'][-1]['collision_status'],'CLEAR')
 def test_boundary_and_small_penetration(self):
  a=box([0,0,0],[1,1,1]);b=box([1,0,0],[2,1,1])
  self.assertEqual(evaluate_pair(a,b,'frame1','frame2',['0','1'],'A')['status'],'COLLISION')
  b['lo'][0]='999999999999/1000000000000';self.assertEqual(evaluate_pair(a,b,'frame1','frame2',['0','1'],'A')['status'],'COLLISION')
 def test_continuity_defect_and_unknown(self):
  state={'punch':box([0,0,0],[1,1,1],[1,0,0])};end=advance(state)
  stages=[{'phase':'OUT','time':['0','1'],'state':state},{'phase':'RETURN','time':['1','2'],'state':end}]
  self.assertEqual(continuity_status(assess_continuity(stages,[])),'CONTINUOUS')
  for mode in ('position','time','lifecycle','unknown'):
   s=copy.deepcopy(stages)
   if mode=='position':s[1]['state']['punch']['lo'][0]='10'
   if mode=='time':s[1]['time'][0]='3/2'
   if mode=='lifecycle':s[1]['state']={}
   if mode=='unknown':s[0]['state']['punch']['delta']=None
   self.assertEqual(continuity_status(assess_continuity(s,[])),'INDETERMINATE' if mode=='unknown' else 'BLOCKED',mode)
if __name__=='__main__':unittest.main()
