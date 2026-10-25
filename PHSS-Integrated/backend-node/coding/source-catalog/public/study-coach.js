/* Transparent study policy: local request parsing and attempt-based recommendations. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.StudyCoach=api;})(globalThis,function(){
 function parse(wish,companies,topics){
  const text=wish.toLowerCase(),normalize=s=>s.toLowerCase().replace(/[^a-z0-9]/g,'');
  const company=[...companies].sort((a,b)=>b.length-a.length).find(c=>(' '+text.replace(/[^a-z0-9]/g,' ')+' ').includes(' '+c.replaceAll('-',' ')+' '));
  const aliases={'arrays':'Array','array':'Array','strings':'String','string':'String','stacks':'Stack','stack':'Stack','binary search':'Binary Search','dynamic programming':'Dynamic Programming','dp':'Dynamic Programming','trees':'Tree','tree':'Tree','graphs':'Graph','graph':'Graph','hash maps':'Hash Table','hash map':'Hash Table','linked list':'Linked List'};
  let topic=[...topics].sort((a,b)=>b.length-a.length).find(t=>text.includes(t.toLowerCase()));
  for(const a of Object.keys(aliases).sort((a,b)=>b.length-a.length))if(new RegExp('\\b'+a+'\\b').test(text)&&topics.includes(aliases[a])){topic=aliases[a];break;}
  const match=text.match(/\b(easy|medium|hard)\b/);
  return {company:company||'',topic:topic||'',difficulty:match?match[1][0].toUpperCase()+match[1].slice(1):''};
 }
 function recommend(problems,attempts,currentId){
  const latest=new Map();for(const a of attempts)if(!latest.has(a.questionId))latest.set(a.questionId,a);
  const current=latest.get(currentId),status=(current?.serverResult||current?.result)?.status;
  if(['syntax_error','runtime_error','wrong_answer','timeout'].includes(status))return {questionId:currentId,action:'retry',reason:'Review the actual diagnostic and failing input, then retry this problem before moving on.'};
  const fresh=problems.filter(p=>!latest.has(p.questionId));const next=fresh.find(p=>p.executionReady)||fresh.find(p=>p.contentAvailable)||problems.find(p=>p.executionReady)||problems[0];
  return next?{slug:next.slug,questionId:next.questionId,action:'next',reason:next.executionReady?'Try this matching problem with supplied tests.':'This matches your request in exploratory mode; no correctness grade is available.'}:{action:'empty',reason:'No matching problems. Broaden your company, topic or difficulty filters.'};
 }
 return {parse,recommend};
});
