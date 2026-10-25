"""Structured scripts for narrated, illustrated short lessons."""
from app.orchestrator.intelligence import generate

def lesson_video(topic):
    result=generate('Create a clear narrated mini-lesson about '+topic+'. Aim for 2–3 minutes total, 5–7 scenes, each with 40–60 spoken words. Start with the goal, explain the idea, demonstrate a worked example, show a common mistake, and recap. Return {"title":"title","slides":[{"title":"short heading","caption":"short on-screen summary, max 180 characters","narration":"full spoken explanation","bullets":["short point","short point"],"code":"optional Python example, at most 6 short lines","visual":{"kind":"array or steps","values":["85","92","78"],"highlight":[1]}}]}. Use visual values/highlights only when they match the explanation; otherwise use steps with 2–4 short labels. Use correct indexing, arithmetic and examples. Never invent citations. No markdown fences.')
    slides=result.get('slides',[])
    if not isinstance(slides,list) or not 3<=len(slides)<=8:
        raise ValueError('Invalid narrated lesson script. Please retry.')
    cleaned=[]
    for s in slides:
        if not isinstance(s,dict) or not isinstance(s.get('narration'),str) or not s['narration'].strip():
            raise ValueError('The generated lesson is missing narration. Please regenerate it.')
        visual=s.get('visual') if isinstance(s.get('visual'),dict) else {}
        values=visual.get('values',[])
        values=[str(x)[:35] for x in values[:8]] if isinstance(values,list) else []
        highlights=visual.get('highlight',[])
        highlights=[i for i in highlights if type(i) is int and 0<=i<len(values)] if isinstance(highlights,list) else []
        bullets=s.get('bullets',[])
        cleaned.append({'title':str(s.get('title',''))[:90],'caption':str(s.get('caption',''))[:180],'narration':s['narration'][:1400],'bullets':[str(b)[:100] for b in bullets[:3]] if isinstance(bullets,list) else [],'code':str(s.get('code',''))[:500], 'visual':{'kind':'array' if visual.get('kind')=='array' else 'steps','values':values,'highlight':highlights}})
    return {'title':str(result.get('title',topic))[:120],'slides':cleaned,'generated':True,'format':'narrated_illustrated_lesson'}
