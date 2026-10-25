import unittest
from unittest.mock import patch, MagicMock
from app.agents.cacm import replay, concept_key
from app.orchestrator.routing import route
from app.orchestrator.graph import run_orchestrator

class IntegrationTests(unittest.TestCase):
    def test_provisional_code_never_changes_mastery(self):
        r=replay('u',[dict(id='1',concept='arrays',agent='coding',kind='code',verified=False,performance=1)])
        self.assertEqual(r['concepts'],[]);self.assertEqual(r['provisionalEvidence'],1)
    def test_dedup_and_cross_agent_conflict(self):
        a=dict(id='q',concept='binary_search',agent='learning',kind='quiz',verified=True,performance=1)
        b=dict(id='c',concept='Binary Search',agent='coding',kind='code_submission',verified=True,performance=0)
        r=replay('u',[a,a,b]);self.assertEqual(r['verifiedEvidence'],2)
        self.assertEqual(len(r['concepts']),1);self.assertEqual(r['concepts'][0]['next_action'],'diagnostic')
    @patch('app.orchestrator.routing.generate',side_effect=RuntimeError('offline'))
    def test_ordered_local_handoff(self,_):
        r=route('Teach me binary search and then give me a coding problem')
        self.assertEqual(r['selected_agents'],['learning','coding']);self.assertEqual(r['concept'],'binary search')
    @patch('app.orchestrator.routing.generate',return_value={'concept':'recursion','selected_agents':['unknown']})
    def test_invalid_semantic_route_falls_back(self,_):
        self.assertEqual(route('debug this code')['selected_agents'],['coding'])
    @patch('app.orchestrator.routing.generate',side_effect=RuntimeError('offline'))
    def test_explicit_learning_mode(self,_):
        self.assertEqual(route('Explain the transformer paper','learning')['selected_agents'],['learning'])
    def test_multi_agent_execution_keeps_success_after_failure(self):
        decision={'concept':'recursion','selected_agents':['learning','coding'],'reason':'test'}
        with patch('app.orchestrator.graph.route',return_value=decision),patch('app.agents.cacm.snapshot',return_value={'concepts':[]}),patch('app.orchestrator.graph.generate',side_effect=[{'explanation':'Use a base case'},{'explanation':'Use recursion','code':'def f(): pass'}]),patch('app.agents.learning.service.create_learning_plan',side_effect=RuntimeError('search unavailable')):
            r=run_orchestrator('u','teach and code recursion')
        self.assertEqual(len(r['agent_results']),2);self.assertIn('plan_error',r['agent_results'][0]);self.assertTrue(r['agent_results'][1]['success'])
    def test_existing_roadmap_reused(self):
        decision={'concept':'arrays','selected_agents':['learning'],'reason':'test'}
        with patch('app.orchestrator.graph.route',return_value=decision),patch('app.agents.cacm.snapshot',return_value={}),patch('app.orchestrator.graph.generate',return_value={'explanation':'Arrays'}),patch('app.agents.learning.service.create_learning_plan',return_value={'existing_found':True,'existing_plan':{'steps':[{'title':'Arrays'}]}}):
            r=run_orchestrator('u','teach arrays')
        self.assertEqual(r['agent_results'][0]['plan']['steps'][0]['title'],'Arrays')
if __name__=='__main__': unittest.main()
