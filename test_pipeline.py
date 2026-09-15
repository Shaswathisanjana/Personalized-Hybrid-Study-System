import asyncio
import logging
logging.basicConfig(level=logging.DEBUG)

from app.agents.search.sources.arxiv import search_arxiv
from app.agents.reading.pdf_parser import parse_pdf_with_fallback
from app.agents.reading.extractor import extract_structured_info
from app.agents.reading.embedder import embed_and_store
from app.knowledge_base.chroma_client import KnowledgeBase

_kb = KnowledgeBase()

async def test():
    print("=== Step 1: Search arXiv ===")
    papers = await search_arxiv('PCB defect detection', limit=2)
    print(f"Got {len(papers)} papers")
    for p in papers:
        abs_len = len(p.abstract or "")
        print(f"  - {p.title[:55]} | pdf_url={bool(p.pdf_url)} | abstract_len={abs_len}")

    if not papers:
        print("NO PAPERS FOUND - stopping")
        return

    p = papers[0]
    print(f"\n=== Step 2: Parse PDF for '{p.title[:40]}' ===")
    try:
        text, conf = await parse_pdf_with_fallback(p)
        print(f"  text_len={len(text)}, confidence={conf}")
    except Exception as e:
        print(f"  PDF PARSE ERROR: {type(e).__name__}: {e}")
        text = p.abstract or ""
        conf = 0.3

    print(f"\n=== Step 3: LLM Extract ===")
    try:
        ext = await extract_structured_info(p, text)
        print(f"  OK: backbone={ext.backbone}, datasets={ext.datasets_used}")
        print(f"      accuracy={ext.accuracy}, f1={ext.f1_score}")
    except Exception as e:
        import traceback
        print(f"  EXTRACT ERROR: {type(e).__name__}: {e}")
        traceback.print_exc()
        return

    print(f"\n=== Step 4: Embed & Store ===")
    try:
        await embed_and_store(_kb, ext, text, p, "test_run")
        print("  OK")
    except Exception as e:
        print(f"  EMBED ERROR: {type(e).__name__}: {e}")

asyncio.run(test())
