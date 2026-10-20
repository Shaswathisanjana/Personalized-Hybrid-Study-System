import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'research'))
from pipeline import verified_claims,validate_gaps,HEAD
class EvidenceTests(unittest.TestCase):
 def test_rejects_invented_quote(self):
  c={'text':'Evaluation is limited to a single small dataset.','page':4,'section':'limitations'}
  rows=verified_claims({'limitations':[{'claim':'Small dataset','quote':c['text']},{'claim':'Made up','quote':'There is no external validation on any dataset.'}]},c,'p1',0)
  self.assertEqual(len(rows),1);self.assertEqual(rows[0]['page'],4)
 def test_gap_requires_real_evidence_from_two_papers(self):
  g=dict(title='External validity',rationale='Limited evaluation',research_question='Does it transfer?',proposed_experiment='Test a new dataset',evidence_ids=['a','b'])
  e=[{'id':'a','paper_id':'p1'},{'id':'b','paper_id':'p2'}]
  self.assertEqual(len(validate_gaps({'gaps':[g]},e)),1)
  self.assertEqual(validate_gaps({'gaps':[g]},e[:1]),[])
  self.assertEqual(validate_gaps({'gaps':[g]},[{'id':'a','paper_id':'p1'},{'id':'b','paper_id':'p1'}]),[])
 def test_section_heading(self):
  self.assertIsNotNone(HEAD.match('6.2 Limitations'))
  self.assertIsNone(HEAD.match('Our method has limitations for small samples.'))

class ClusterTests(unittest.TestCase):
 def test_empty_singleton_and_semantic_vectors(self):
  from pipeline import cluster_evidence
  import numpy as np
  class Encoder:
   def encode(self, texts, **kwargs): return np.array([[1.,0.],[.99,.01],[0.,1.]][:len(texts)])
  e=[{'id':str(i),'paper_id':'p'+str(i),'quote':'Evidence '+str(i)} for i in range(3)]
  self.assertEqual(cluster_evidence([],Encoder()),[])
  self.assertEqual(len(cluster_evidence(e[:1],Encoder())),1)
  clusters=cluster_evidence(e,Encoder())
  self.assertEqual(sorted(len(c['evidence_ids']) for c in clusters),[1,2])

if __name__=='__main__':unittest.main()
