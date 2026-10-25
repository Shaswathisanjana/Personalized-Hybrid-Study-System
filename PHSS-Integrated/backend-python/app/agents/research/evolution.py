"""Bounded automatic, source-grounded research progression review."""
from datetime import datetime, timezone
import re

MAX_ANALYZED = 12

def deduplicate(records, now):
    seen=set();result=[]
    for original in records:
        p=dict(original)
        identity=re.sub(r"v\d+$","",str(p.get("url") or "")).lower().rstrip("/")
        identity=identity or re.sub(r"\W+"," ",p.get("title","").lower()).strip()
        if not identity or identity in seen:continue
        date=str(p.get("published") or p.get("year") or "")
        if date[:10] > now.date().isoformat():continue
        seen.add(identity);p["source_id"]="S"+str(len(result)+1);result.append(p)
    return result

def checked_selection(data, candidates):
    requested=data.get("selected_ids")
    if not isinstance(requested,list):raise ValueError("The research selector returned no source list.")
    if any(not isinstance(value,str) for value in requested):
        raise ValueError("Invalid source identifier in research selection.")
    wanted=set(requested)
    if not wanted <= {p["source_id"] for p in candidates}:
        raise ValueError("The selector referenced a paper that was not retrieved.")
    selected=[p for p in candidates if p["source_id"] in wanted]
    if not selected:raise ValueError("No relevant sources were selected. Try a more specific research topic.")
    if len(selected)>MAX_ANALYZED:raise ValueError("The research selector exceeded its processing budget.")
    return selected

def checked_synthesis(data, source_ids):
    """Reject invented references and unsupported narrative objects."""
    result={}
    for field in ("timeline","current_state","comparisons","gaps","future_work"):
        values=data.get(field,[])
        if not isinstance(values,list):raise ValueError("Invalid research synthesis format.")
        rows=[]
        for row in values:
            if not isinstance(row,dict) or not row.get("title") or not row.get("description"):continue
            refs=row.get("source_ids")
            if not isinstance(refs,list) or not refs or not set(refs)<=source_ids:
                raise ValueError("Research synthesis included missing or unknown evidence references.")
            item={"title":str(row["title"])[:400],"description":str(row["description"])[:10000],
                  "source_ids":list(dict.fromkeys(refs)),"period":str(row.get("period",""))[:100]}
            if field=="gaps":
                for key in ("existing_work","unresolved_limitation","why_it_matters"):
                    if isinstance(row.get(key),str):
                        item["description"] += "\n\n"+key.replace("_"," ").capitalize()+": "+row[key]
            if field=="future_work":
                item["experiment"]={key:str(value)[:5000] for key,value in (row.get("experiment") or {}).items()
                    if key in {"research_question","hypothesis","implementation","data","baselines","metrics","validation","risks"} and isinstance(value,str)}
            rows.append(item)
        result[field]=rows
    if not result["current_state"]:raise ValueError("No supported current-state summary was generated.")
    result["section_warnings"]=[str(x)[:1000] for x in data.get("section_warnings",[]) if isinstance(x,str)]
    result["learning_concepts"]=[str(c)[:200] for c in data.get("learning_concepts",[]) if isinstance(c,str)][:10]
    return result

def retrieve(topic, now):
    import arxiv
    from src.arxiv_search import is_survey_paper
    tokens=[t for t in re.findall(r"[A-Za-z0-9]+",topic) if t.lower() not in {"i","want","wanted","research","on","about","and","the","a","to","please","need"}]
    if not tokens:raise ValueError("Enter a research topic.")
    query=" AND ".join('all:"'+t+'"' for t in tokens[:14])
    if re.search(r"\bagentic\b",topic,re.I) and re.search(r"multi[ -]?agent",topic,re.I):
        query='(all:"agentic AI" OR all:"LLM agents" OR all:"large language model agents") AND (all:"multi-agent" OR all:"multiagent" OR all:"agent collaboration")' 
    client=arxiv.Client(page_size=14,delay_seconds=3,num_retries=1)
    records=[];errors=[]
    searches=[(query,arxiv.SortCriterion.Relevance),
              (query,arxiv.SortCriterion.SubmittedDate),
              (query+' AND (ti:survey OR ti:review)',arxiv.SortCriterion.SubmittedDate)]
    for q,sort in searches:
        try:
            for p in client.results(arxiv.Search(query=q,max_results=14,sort_by=sort,sort_order=arxiv.SortOrder.Descending)):
                records.append({"title":p.title,"abstract":p.summary,"authors":[a.name for a in p.authors],
                    "published":p.published.isoformat(),"url":p.entry_id,"pdf_url":p.pdf_url,"source":"arXiv",
                    "is_survey":is_survey_paper(p.title,p.summary)})
        except Exception as exc:errors.append(type(exc).__name__)
    if len(deduplicate(records,now)) < 8:
        from src.semantic_scholar_search import search_semantic_scholar
        for p in search_semantic_scholar(topic,limit=40,exclude_reviews=False):
            p=dict(p);p["is_survey"]=is_survey_paper(p.get("title",""),p.get("abstract",""));records.append(p)
    return deduplicate(records,now),errors

def automatic_review(user_id, topic):
    # Import the existing Unified pipeline lazily and retain its PDF evidence extraction.
    from app.agents.research.service import VENDOR_DIR
    import sys,json
    if str(VENDOR_DIR) not in sys.path:sys.path.insert(0,str(VENDOR_DIR))
    from app.orchestrator.intelligence import generate
    from src.pdf_sections import PDFSectionExtractor
    from src.paper_analysis import PaperAnalyzer
    from app.database.mongo import get_db
    now=datetime.now(timezone.utc)
    candidates,errors=retrieve(topic,now)
    if not candidates:raise RuntimeError("No usable papers were retrieved for this topic. Broaden the topic and retry.")
    brief=[{k:(str(p.get(k))[:2500] if k=="abstract" else p.get(k)) for k in ("source_id","title","abstract","published","is_survey","url")} for p in candidates]
    selection=generate('Select papers for an evidence-based research progression review of '+topic+
        '. Balance primary technical studies with surveys. Prefer evidence for architectures, planning, tool use, memory, coordination and evaluation; do not let security/governance dominate a broad technical topic. Include older foundational evidence when retrieved and recent developments. Explain missing facets; do not call the set comprehensive. Choose the smallest useful set based on relevance, temporal coverage, distinct contributions, and available surveys. Include a relevant recent survey if available plus primary evidence where useful. Do not fill a fixed quota. Processing cap is 12 sources. Return {"selected_ids":["S1"],"reason":"why this set is sufficient within the budget; note any missing historical or recent coverage"}. Candidates: '+json.dumps(brief,default=str))
    selected=checked_selection(selection,candidates)
    if len(selected)<3:
        raise RuntimeError("Retrieval produced too little relevant evidence for a research-progression review. No field-wide conclusions were generated. Refine the topic and retry.")
    extracted=PDFSectionExtractor().extract_papers(selected)
    analyses=PaperAnalyzer().analyze_papers(topic,extracted)
    # Attach identity by title, without assuming extraction preserved order.
    from src.provenance import source_key
    by_source={source_key(p.get("url")):p for p in selected}
    extracted_by_source={source_key(p.get("url")):p for p in extracted}
    evidence=[]
    for a in analyses:
        source=by_source.get(source_key(a.get("url")))
        if source:
            from app.agents.research.evidence_context import pack_evidence
            fields=pack_evidence({**a,"source_id":source["source_id"],"published":source.get("published"),"is_survey":source.get("is_survey")})
            evidence.append(fields)
    from app.agents.research.synthesis import detailed_synthesis
    output=detailed_synthesis(topic,now.date().isoformat(),evidence,generate)
    summary=checked_synthesis(output,{p["source_id"] for p in evidence})
    dates=[str(p.get("published") or p.get("year") or "") for p in selected if p.get("published") or p.get("year")]
    report={"review_mode":"evolution","topic":topic,"papers":selected,"paper_analyses":analyses,
        "research_progression":summary,"selection_reason":str(selection.get("reason",""))[:3000],
        "coverage":{"searched_at":now.isoformat(),"latest_included_publication":max(dates) if dates else None,
            "candidates_found":len(candidates),"analyzed":len(evidence),"full_text_available":sum(bool(p.get("full_text_extracted")) for p in evidence),"survey_papers":sum(bool(p.get("is_survey")) for p in selected),
            "processing_cap":MAX_ANALYZED,"search_warnings":errors,
            "limitations":"Bounded search of arXiv, with Semantic Scholar used if arXiv yields no records. Recent indexing delays, source availability, retrieval relevance and PDF extraction limit coverage. This is not an exhaustive review through today."},
        "research_gap_synthesis":"\n\n".join(x["title"]+": "+x["description"]+" ["+", ".join(x["source_ids"])+"]" for x in summary["gaps"]),
        "userId":user_id,"createdAt":now}
    try:
        stored=dict(report);stored["jobId"]=str(get_db().research_jobs.insert_one(dict(report)).inserted_id)
        report["jobId"]=stored["jobId"]
    except Exception:
        report["persistence_warning"]="This review could not be saved; download it before leaving."
    return report
