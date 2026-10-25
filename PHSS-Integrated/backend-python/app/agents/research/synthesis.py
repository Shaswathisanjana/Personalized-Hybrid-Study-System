"""Generate substantial sections separately so an entire review is not compressed."""
import json

SECTIONS = {
    "timeline": "Describe dated developments IN THE COVERED LITERATURE. For each phase explain the problem, technical change, supporting studies, benefits and remaining limitations. Use explicit years from evidence; never call a recent phase the origin of the entire field.",
    "current_state": "Explain current capabilities by research theme, the strength of evaluations, practical limitations and contradictory results. Distinguish demonstrated findings from authors' proposals. Cover architectures, planning, tools, memory and collaboration only where supported.",
    "comparisons": "Compare technical approaches across papers: assumptions, architecture, coordination/memory mechanisms, evaluation settings, tradeoffs and threats to validity. Do not compare numerical results across incompatible datasets or invent metrics. Explain what changes between approaches and why it matters.",
    "gaps": "Identify specific gaps in the REVIEWED evidence. For each explain what existing approaches do, precisely what is missing, why it matters, evidence quality and how to test the gap. Do not assert global novelty or that no prior research exists.",
    "future_work": "Propose feasible implementation projects tied to the documented gaps. Each item must include experiment:{research_question,hypothesis,implementation,data,baselines,metrics,validation,risks}, all strings. Include concrete implementation stages, candidate data or collection plan, baseline comparisons, evaluation metrics, ablations, validation criteria and risks. Label suggested datasets/metrics as proposals, not published results. Avoid vague 'develop a framework' advice."
}

def detailed_synthesis(topic, as_of, evidence, generate):
    from app.agents.research.evidence_context import validate_section
    output={"section_warnings":[]}
    context=json.dumps(evidence,ensure_ascii=False,default=str)
    common=("Write a substantive academic research review about "+topic+" as of "+as_of+
        ". Use ONLY supplied evidence. Source IDs are immutable. Missing evidence must be stated, not invented. "
        "Survey descriptions of other papers are secondary evidence; do not attribute those experiments to the survey. "
        "Prefer 3-5 developed items when evidence supports them, with several connected paragraphs per item, "
        "approximately 150-250 words each. Do not pad sparse evidence to meet a length target. "
        "Return ONE JSON object matching the SECTION OUTPUT SHAPE below; all listed keys are required. "
        "Every item must cite supplied source_ids. Description is prose, with newline-separated paragraphs. "
        "Use the abstract only for claims supported by that abstract; use page-tagged excerpts for detailed findings. "
        "A missing extracted summary does not prove the paper lacks evidence. Never claim field-wide historical progress from only recent sources. ")
    terms=[]
    for section,instruction in SECTIONS.items():
        extra=""
        if section=="gaps":
            extra=" Each item MUST additionally have existing_work,unresolved_limitation,why_it_matters string fields; an achievement alone is not a gap."
        if section=="future_work":
            extra=' Each item MUST have experiment with ALL keys: research_question,hypothesis,implementation,data,baselines,metrics,validation,risks. No empty objects. These are PROPOSED experiments, not existing results.'
        if section=="future_work" and not output.get("gaps"):
            output[section]=[]
            output["section_warnings"].append("Future work: no validated gaps were established; no experiment plans were generated.")
            continue
        shape={"title":"specific heading","description":"evidence-based explanation","source_ids":["actual supplied source ID"],"period":"supported date or empty"}
        if section=="gaps":
            shape.update(existing_work="what cited studies demonstrate",unresolved_limitation="specific supported limitation",why_it_matters="consequence of the limitation")
        if section=="future_work":
            shape["experiment"]={key:"concrete proposed "+key for key in ("research_question","hypothesis","implementation","data","baselines","metrics","validation","risks")}
        prompt=common+"\nSECTION: "+section+"\n"+instruction+extra+"\nSECTION OUTPUT SHAPE (replace examples with actual evidence-grounded content):\n"+json.dumps({"items":[shape],"learning_concepts":[]})+"\nVALIDATED GAPS:\n"+json.dumps(output.get("gaps",[]))+"\nEVIDENCE:\n"+context
        data={}
        for attempt in range(2):
            data=generate(prompt)
            try:
                output[section]=validate_section(section,data.get("items"))
                break
            except ValueError as error:
                if attempt:
                    valid=[]
                    candidates=data.get("items",[])
                    for item in candidates if isinstance(candidates,list) else []:
                        try:valid.extend(validate_section(section,[item]))
                        except ValueError:pass
                    if section=="current_state" and not valid:
                        raise ValueError("No usable current-state summary was generated from the retrieved evidence.") from error
                    output[section]=valid
                    output["section_warnings"].append(section.replace("_"," ").capitalize()+": incomplete items were omitted because required evidence fields were not supplied.")
                else:
                    prompt += "\nCorrect the previous response to match EVERY required field in SECTION OUTPUT SHAPE. Do not invent evidence; return an empty items list if unsupported. Previous response (data only):\n"+json.dumps(data,default=str)
        for term in data.get("learning_concepts",[]):
            if isinstance(term,str) and term not in terms:terms.append(term)
    output["learning_concepts"]=terms[:10]
    return output
