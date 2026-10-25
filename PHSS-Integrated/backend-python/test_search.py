import time
import sys
from pathlib import Path

start = time.time()
from app.agents.research.service import search_papers
print(f"Imported search_papers in {round(time.time() - start, 2)} s")

t0 = time.time()
res = search_papers("test_user", "PCB Defect Detection", 5)
print(f"search_papers completed in {round(time.time() - t0, 2)} s")
print("Keys:", list(res.keys()))
print("Papers count:", len(res["papers"]))
if res.get("papers"):
    print("Top paper:", res["papers"][0].get("title"))
