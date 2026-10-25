"""Static Python diagnosis only. Never executes a student's program."""
import ast
import re

def looks_like_code(message):
    if re.search(r"(?:^|\n)\s*[A-Za-z_]\w*\s*=\s*[^=]",message):
        return True
    return bool(re.search(r'```(?:python|py)?\s*\n|\b(?:print|input)\s*\(|(?:^|\n)\s*(?:async\s+def |def |class |from\s+\w+.*\simport |import\s+\w+|for\s+\w+\s+in\s+|while\s+.+:|if\s+.+:)',message))

def extract_code(message):
    fenced=re.search(r'```(?:python|py)?\s*\n(.*?)```',message,re.S|re.I)
    if fenced:return fenced.group(1).strip('\n')
    lines=message.splitlines()
    for i,line in enumerate(lines):
        if re.search(r'^\s*(?:[A-Za-z_]\w*\s*=|def |class |import |from |for |while |if |print\s*\()',line):
            # Trim a trailing natural-language request, preserving indentation.
            tail=lines[i:]
            while tail and re.match(r'^\s*(?:find (?:the )?error|debug (?:this|the)|please (?:fix|debug)|what is (?:the )?(?:error|wrong))\b',tail[-1],re.I):tail.pop()
            return '\n'.join(tail)
    return message

def diagnose(message):
    if not looks_like_code(message):return None
    source=extract_code(message)
    try:
        ast.parse(source)
        return {'valid_syntax':True,'message':'Python syntax check passed. Logic and runtime behavior have not been tested.','code':source}
    except SyntaxError as exc:
        text=(exc.text or '').rstrip('\n')
        pointer=' ' * max(0,(exc.offset or 1)-1)+'^'
        return {'valid_syntax':False,'message':f'{type(exc).__name__} on line {exc.lineno}, column {exc.offset}: {exc.msg}\n{text}\n{pointer}\nThis is a static syntax check; the program was not executed.','code':source}
