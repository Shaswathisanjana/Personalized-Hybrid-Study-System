"""Lossless snippet extraction for review intents; never executes code."""
import re

PROSE=re.compile(r"^(?:(?:please\s+)?(?:is (?:this|my|the) (?:python )?code correct|check (?:this|my|the) code|review (?:this|my|the) code|fix (?:this|my|the) code|can you (?:check|review|fix)|what is wrong|why (?:does|is)|expected (?:output|behavior)|it should)\b)",re.I)
CODE=re.compile(r"^(?:async\s+def\b|def\s|class\s|from\s|import\s|(?:if|for|while|with)\b.*:|try\s*:|[A-Za-z_]\w*\s*(?:=|\(|\[)|#)")

def extract_review_code(query):
    """Prefer explicit fences; otherwise separate surrounding request lines.

    A damaged program remains reviewable. We do not require ast.parse success
    and do not ask a provider to rewrite/extract the student's source.
    """
    fenced=list(re.finditer(r"```(?:python|py)?[ \t]*\r?\n(.*?)```",query,re.S|re.I))
    if len(fenced)>1:return ''  # Ask the student which snippet to inspect.
    if fenced:return fenced[0].group(1).strip('\r\n')
    lines=query.splitlines(keepends=True)
    start=next((i for i,line in enumerate(lines) if CODE.match(line.lstrip())),None)
    if start is None:return ''
    end=len(lines)
    for i in range(start+1,len(lines)):
        if lines[i] and not lines[i][0].isspace() and PROSE.match(lines[i].strip()):
            end=i;break
    return ''.join(lines[start:end]).strip('\r\n')

def fallback_review_request(query):
    """Conservative supplemental fallback, not the primary semantic router."""
    code=extract_review_code(query)
    request=query.replace(code,'',1) if code else query
    return bool(code and re.search(r'\b(?:correct|review|debug|fix|wrong|error|check)\b',request,re.I))
