
from semantic_scholar_search import search_semantic_scholar

TOPIC = "PCB defect detection deep learning"

papers = search_semantic_scholar(TOPIC, limit=50)

print(f"\nOriginal research candidates: {len(papers)}")

for i, paper in enumerate(papers[:10], start=1):
    print(f"\n{i}. {paper['title']}")
    print(f"Year: {paper['year']}")
    print(f"Citations: {paper['citation_count']}")
    print(f"Retrieval score: {paper['retrieval_score']:.3f}")
    print(f"Abstract available: {bool(paper['abstract'])}")
    print(f"PDF: {paper['pdf_url']}")
    print(f"Paper: {paper['url']}")
