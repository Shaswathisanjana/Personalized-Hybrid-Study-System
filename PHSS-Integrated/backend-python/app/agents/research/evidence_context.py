"""Preserve evidence by field, rather than truncating one concatenated dictionary."""
FIELDS=("methodology","dataset","results_metrics","author_stated_limitations","future_work")
EXPERIMENT_FIELDS=("research_question","hypothesis","implementation","data","baselines","metrics","validation","risks")

def pack_evidence(record):
    packed={key:record.get(key) for key in ("source_id","title","published","is_survey","abstract","full_text_extracted")+FIELDS}
    packed["retrieved_evidence"]={}
    for field in FIELDS:
        chunks=(record.get("retrieved_evidence") or {}).get(field,[])
        packed["retrieved_evidence"][field]=[
            {"pages":str(c.get("pages","unknown")),"heading":str(c.get("heading","")),
             "text":str(c.get("text",""))[:1400]} for c in chunks[:3]]
    packed["interpretation_rule"]="An unavailable summary means extraction did not establish the field, not that the paper contains no relevant information. Distinguish abstract evidence from page-tagged excerpts."
    return packed

def validate_section(section,items):
    if not isinstance(items,list) or not items:
        raise ValueError("The writer returned no usable "+section+" items.")
    for item in items:
        if not isinstance(item,dict) or not item.get("description") or not item.get("source_ids"):
            raise ValueError("Research section lacks narrative or sources.")
        if section=="gaps":
            for field in ("existing_work","unresolved_limitation","why_it_matters"):
                if not isinstance(item.get(field),str) or not item[field].strip():
                    raise ValueError("A research gap must distinguish existing work from an unresolved limitation.")
        if section=="future_work":
            experiment=item.get("experiment")
            if not isinstance(experiment,dict) or any(not isinstance(experiment.get(k),str) or not experiment[k].strip() for k in EXPERIMENT_FIELDS):
                raise ValueError("A future-work item is missing an actionable experiment plan.")
    return items
