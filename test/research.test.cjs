const {test}=require('node:test'), assert=require('node:assert/strict');
const {createGemini}=require('../ai/gemini.cjs');
test('Gemini adapter maps LangChain roles and rejects incomplete generation',async()=>{
 let sent;
 const llm=createGemini({env:{GEMINI_API_KEY:'fake',GEMINI_MODEL:'test'},request:async(url,init)=>{sent=JSON.parse(init.body);return {ok:true,json:async()=>({candidates:[{finishReason:'STOP',content:{parts:[{text:'{"ok":true}'}]}}]})};}});
 const result=await llm.invoke([{_getType:()=> 'system',content:'Return JSON'},{_getType:()=> 'human',content:'hello'}]);
 assert.equal(result.content,'{"ok":true}');assert.equal(sent.systemInstruction.parts[0].text,'Return JSON');assert.equal(sent.contents[0].role,'user');assert.equal(sent.generationConfig.responseMimeType,'application/json');
 const incomplete=createGemini({env:{GEMINI_API_KEY:'fake'},request:async()=>({ok:true,json:async()=>({candidates:[{finishReason:'MAX_TOKENS',content:{parts:[{text:'{}'}]}}]})})});
 await assert.rejects(incomplete.invoke([]),/incomplete/);
});
test('missing key disables generation',()=>assert.equal(createGemini({env:{}}),null));
test('Gemini HTTP status is preserved for user-facing error handling',async()=>{
 const llm=createGemini({env:{GEMINI_API_KEY:'fake'},request:async()=>({ok:false,status:429})});
 await assert.rejects(llm.invoke([]),e=>e.status===429);
});
test('research API scopes jobs, restricts output files and rejects invalid inputs',async()=>{
 const express=require('express'),fs=require('node:fs/promises'),os=require('node:os'),path=require('node:path');
 const {installResearch}=require('../research/index.cjs');const root=await fs.mkdtemp(path.join(os.tmpdir(),'cacm-test-'));
 const app=express();app.use(express.json());installResearch({app,outputRoot:root});
 const server=await new Promise(resolve=>{const s=app.listen(0,'127.0.0.1',()=>resolve(s));});
 const base='http://127.0.0.1:'+server.address().port;
 try {
  assert.equal((await fetch(base+'/api/research/jobs?userId=bad%20id')).status,400);
  const id='12345678-1234-1234-1234-123456789012';await fs.mkdir(path.join(root,'alice',id),{recursive:true});await fs.writeFile(path.join(root,'alice',id,'status.json'),JSON.stringify({phase:'completed'}));
  assert.equal((await fetch(base+'/api/research/jobs/'+id+'?userId=bob')).status,404);
  assert.equal((await fetch(base+'/api/research/jobs/'+id+'/files/request.json?userId=alice')).status,404);
  const r=await fetch(base+'/api/research/jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({userId:'alice',topic:'test',count:11})});assert.equal(r.status,400);
 } finally {await new Promise(r=>server.close(r));await fs.rm(root,{recursive:true,force:true});}
});
