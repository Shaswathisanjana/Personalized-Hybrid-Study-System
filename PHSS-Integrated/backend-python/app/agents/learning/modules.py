"""Curriculum modules are independent of how many search results were found."""
def build_modules(ordered_concepts, resources, level):
    def data(resource):
        return resource.model_dump() if hasattr(resource, "model_dump") else dict(resource)
    readings=[data(r) for r in resources]
    names=list(dict.fromkeys([str(c) for c in ordered_concepts if c]+[
        str(r.get("target_concept") or r.get("concept"))
        for r in readings if r.get("target_concept") or r.get("concept")]))
    steps=[]
    for order,name in enumerate(names,1):
        matches=[r for r in readings if (r.get("target_concept") or r.get("concept"))==name]
        primary=next((r for r in matches if "video" not in str(r.get("format","")).lower()),matches[0] if matches else {})
        steps.append({
            "order":order,"title":name,"concept":name,
            "objective":f"Learn {name}, then check your understanding with the module quiz.",
            "url":primary.get("url",""),"format":primary.get("format","module"),
            "type":primary.get("format","module"),"difficulty":primary.get("difficulty",level),
            "estimated_minutes":primary.get("estimated_minutes",0),
            "snippet":primary.get("snippet",""),
            "materials_available":bool(matches)
        })
    return steps
