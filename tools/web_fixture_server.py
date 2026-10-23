"""Explicit OFFLINE TEST server; never used by production launcher."""
from pathlib import Path
import sys, socket, json
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from unittest.mock import patch
from backend.main import create_app
from backend.service import Application
from test_student_journey_streamlit import RoutedOfflineOrchestrator
from test_unified_query_refinement import real_router,linked_list_package
from test_research_search_collection import PagedFixture,synthetic_paper
from test_verified_coding_catalog import EvaluationGuardrailTests
from app.coding_agent.open_topic import OpenTopicGenerator
from pdf_collection_test_fixtures import ExtractiveAnalyzer

class FixtureRuntime(RoutedOfflineOrchestrator):
    @staticmethod
    def route(query):
        if query.startswith('Please check this code'):
            from backend.tests.test_code_review_flow import semantic_route
            return semantic_route(query)
        return real_router(query)

def serve():
    import uvicorn
    root=Path(__file__).resolve().parents[1]
    application=Application(root/'data/web-browser-fixture.sqlite3',factory=FixtureRuntime)
    from app.coding_agent.ai_code_reviewer import AICodeReviewer
    from backend.tests.test_code_review_flow import review_payload
    def reviewer():
        client=SimpleNamespace(models=SimpleNamespace(generate_content=lambda **_:SimpleNamespace(text=json.dumps(review_payload()))))
        return AICodeReviewer(client=client)
    connect=socket.socket.connect
    def local(sock,address):
        if not isinstance(address,tuple) or address[0] not in ('127.0.0.1','::1'):raise AssertionError('External provider access disabled in fixture server')
        return connect(sock,address)
    with patch('app.coding_agent.guided_review_coordinator.AICodeReviewer',side_effect=reviewer),patch('socket.socket.connect',local),patch('app.research_agent.search_session.AcademicPaperSearch',lambda:PagedFixture([[synthetic_paper(i) for i in range(7)]])),patch('app.coding_agent.integrated_workflow.CodingEvaluator',EvaluationGuardrailTests().evaluator),patch('app.coding_agent.open_topic.OpenTopicGenerator',lambda **kw:OpenTopicGenerator(provider=lambda **_:linked_list_package(),**kw)),patch('app.research_agent.collection_service.GroundedChunkAnalyzer',return_value=ExtractiveAnalyzer()):
        uvicorn.run(create_app(application),host='127.0.0.1',port=8011,log_level='warning')
if __name__=='__main__':serve()
