from app.research_agent.paper_search import AcademicPaperSearch

result = AcademicPaperSearch().search(
    query="Deep Learning for Medical Image Classification",
    limit=5,
)

for paper in result.papers:
    if paper.title.strip().lower() == "deep learning in medical image classification":
        print("\nTITLE:", paper.title)
        print("\nABSTRACT:\n")
        print(paper.abstract or "[EMPTY ABSTRACT]")
        print("\nABSTRACT LENGTH:", len(paper.abstract or ""))
        print("\nSOURCE:", paper.url)
