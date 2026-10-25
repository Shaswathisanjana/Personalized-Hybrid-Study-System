"""Source identity checks; paper order is not an identifier."""
import re
from urllib.parse import urlparse

def source_key(url):
    text=str(url or "").strip()
    match=re.search(r"arxiv\.org/(?:abs|pdf)/([\w.-]+)",text,re.I)
    if match:return "arxiv:"+re.sub(r"v\d+$","",match.group(1).removesuffix(".pdf"))
    parsed=urlparse(text)
    return parsed.netloc.lower()+parsed.path.rstrip("/") if parsed.scheme in {"http","https"} else ""

def validate_pdf_identity(paper,text):
    """Conservative first-page check, not a claim of semantic verification."""
    first=text[:4500].lower()
    key=source_key(paper.get("pdf_url") or paper.get("url"))
    if key.startswith("arxiv:") and key[6:] in first:
        return
    stop={"with","from","that","this","using","based","paper","towards","through","and","the","for"}
    words={w for w in re.findall(r"[a-z0-9]+",str(paper.get("title","")).lower()) if len(w)>2 and w not in stop}
    matches=sum(bool(re.search(r"\b"+re.escape(w)+r"\b",first)) for w in words)
    if len(words)<2 or matches/len(words)<.6:
        raise ValueError("PDF identity could not be matched to the selected paper. Its text will not be used as full-text evidence.")

def supporting_quote_present(parsed, field, chunks):
    """Require at least one verbatim supporting quote from this field's own chunks."""
    quotes=(parsed.get("supporting_quotes") or {}).get(field,[])
    if isinstance(quotes,str):quotes=[quotes]
    if not isinstance(quotes,list):return False
    normalize=lambda value:re.sub(r"\s+"," ",str(value or "")).strip().lower()
    sources=[normalize(chunk.get("text","")) for chunk in chunks]
    return any(isinstance(quote,str) and len(normalize(quote))>=20
               and any(normalize(quote) in source for source in sources) for quote in quotes)
