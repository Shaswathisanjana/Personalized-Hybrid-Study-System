'use strict';
// Gemini REST adapter preserving the existing LangGraph invoke interface.
function createGemini({request = fetch, env = process.env} = {}) {
  if (!env.GEMINI_API_KEY) return null;
  return { async invoke(messages, options = {}) {
    const mapped=messages.map(m=>({role:m.role || (m._getType?.()==='system'?'system':'user'),content:m.content}));
    const system=mapped.filter(m=>m.role==='system').map(m=>m.content).join('\n');
    const response=await request('https://generativelanguage.googleapis.com/v1beta/models/'+encodeURIComponent(env.GEMINI_MODEL || 'gemini-2.5-flash')+':generateContent',{
      method:'POST',headers:{'Content-Type':'application/json','x-goog-api-key':env.GEMINI_API_KEY},
      signal:options.signal || AbortSignal.timeout(60000),
      body:JSON.stringify({systemInstruction:{parts:[{text:system}]},contents:mapped.filter(m=>m.role!=='system').map(m=>({role:m.role==='assistant'?'model':'user',parts:[{text:m.content}]})),generationConfig:{temperature:.2,responseMimeType:'application/json'}})
    });
    if(!response.ok){const e=new Error(`Gemini returned HTTP ${response.status}. Check model access, quota and API configuration.`);e.status=response.status;throw e;}
    const data=await response.json(),candidate=data.candidates?.[0];
    const content=(candidate?.content?.parts || []).filter(p=>!p.thought).map(p=>p.text || '').join('');
    if(candidate?.finishReason!=='STOP' || !content)throw new Error('Gemini returned an incomplete response.');
    return {content};
  }};
}
module.exports={createGemini};
