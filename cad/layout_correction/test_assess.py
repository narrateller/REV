import unittest
from fractions import Fraction as F
from assess import overlap,box_at,classify,checked,NativeWitness

def body(x,delta):return {'lo':[str(x),'0','0'],'hi':[str(F(x)+1),'1','1'],'delta':[str(delta),'0','0'],'motion':'linear','exact_box':True,'group':'test'}
class NewAnalysis(unittest.TestCase):
 def test_positive_and_face_and_edge(self):
  self.assertEqual(overlap(([F(0)]*3,[F(1)]*3),([F(0)]*3,[F(1)]*3))[0],'PENETRATION')
  self.assertEqual(overlap(([F(0)]*3,[F(1)]*3),([F(1),F(0),F(0)],[F(2),F(1),F(1)]))[:2],('TOUCH',F(1)))
  self.assertEqual(overlap(([F(0)]*3,[F(1)]*3),([F(1),F(1),F(0)],[F(2),F(2),F(1)]))[:2],('TOUCH',F(0)))
 def test_midstroke_and_return_are_not_missed(self):
  for x,d in [('-3','6'),('3','-6')]:
   state={'moving':body(x,d),'wall':body('0','0')};r=checked.evaluate_pair(state['moving'],state['wall'],'moving','wall',['0','1'],'A')
   c=classify(r,state,['0','1'],'A');self.assertEqual(c['class'],'PENETRATION');self.assertTrue(any(x['positive_overlap_m3']!='0' for x in c['regions']))
 def test_declaring_contact_never_hides_penetration(self):
  state={'lock':body('0','0'),'end_stop':body('0','0')};r=checked.evaluate_pair(*state.values(),'lock','end_stop',['0','1'],'B')
  self.assertEqual(classify(r,state,['0','1'],'B')['class'],'PENETRATION')
 def test_unknown_is_not_clear(self):
  state={'moving':body('0','0'),'wall':body('0','0')};state['moving']['delta']=None;r=checked.evaluate_pair(*state.values(),'moving','wall',['0','1'],'A')
  self.assertEqual(classify(r,state,['0','1'],'A')['class'],'INDETERMINATE')
 def test_nonpersisted_native_body_is_unknown(self):
  fake=NativeWitness.__new__(NativeWitness);fake.objects={'A':{}}
  self.assertEqual(fake.at('A',['research_obstacle','rod'],{},'0',['0','1'])['status'],'INDETERMINATE')
 def test_bounding_overlap_does_not_claim_native_penetration(self):
  state={'curve':body('0','0'),'box':body('0','0')};state['curve']['exact_box']=False
  r=checked.evaluate_pair(*state.values(),'curve','box',['0','1'],'A');c=classify(r,state,['0','1'],'A')
  self.assertEqual(c['class'],'ENVELOPE_INTERSECTION');self.assertEqual(c['native_solids'],'INDETERMINATE')
if __name__=='__main__':unittest.main()
