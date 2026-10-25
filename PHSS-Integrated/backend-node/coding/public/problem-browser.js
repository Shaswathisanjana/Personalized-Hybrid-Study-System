'use strict';
(()=>{
 const $=id=>document.getElementById(id),SIZE=20;
 let data,items=[],results=[],page=0,selected='',version=0,progress=new Map(),attempts=[],activeQuestionId='',busy=false;
 const node=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
 function link(url,text){const a=node('a',text);a.href=url;a.target='_blank';a.rel='noopener noreferrer';return a;}
 function frequency(p){return p.companies[$('catalogCompany').value]?.[$('catalogPeriod').value]?.frequency ?? -1;}
 function filter(auto=true){
  if(!data)return;
  const q=$('catalogSearch').value.trim().toLowerCase(),diff=$('catalogDifficulty').value,topic=$('catalogTopic').value,company=$('catalogCompany').value,period=$('catalogPeriod').value,ready=$('catalogReady').value,state=$('catalogProgress').value;
  results=items.filter(p=>{const a=progress.get(p.questionId || p.practiceQuestionId);return (!q||[p.title,p.slug,p.problemNumber || '',...p.topics].join(' ').toLowerCase().includes(q))&&(!diff||p.difficulty===diff)&&(!topic||p.topics.includes(topic))&&(!company||p.companies[company]?.[period])&&(!ready||(ready==='ready'?p.executionReady:!p.executionReady))&&(!state||(state==='new'?!a:state==='passed'?a==='passed':Boolean(a)));});
  results.sort((a,b)=>($('catalogSort').value==='frequency'&&company?frequency(b)-frequency(a):0)||a.title.localeCompare(b.title));page=0;render();
  if(auto && results.length && !results.some(p=>p.slug===selected))void open(results[0]);
  if(!results.length){version++;selected='';$('catalogDetail').replaceChildren(node('p','No problem matches these filters. The editor keeps your current draft.'));}

 }
 function render(){
  $('catalogCount').textContent=results.length.toLocaleString()+' matching problems';
  $('catalogNote').textContent=items.filter(p=>p.executionReady).length+' problems have checked grading. Other imported statements open in exploratory Python mode. Company snapshot: '+data.companySnapshot+'.';
  const list=$('catalogList');list.replaceChildren();
  for(const p of results.slice(page*SIZE,(page+1)*SIZE)){
   const b=node('button',undefined,'catalog-row'+(selected===p.slug?' selected':''));b.type='button';b.dataset.slug=p.slug;
   b.append(node('strong',p.title),node('span',p.difficulty+' · '+(p.topics.slice(0,3).join(', ')||'Topics unavailable'),'small'));
   const f=frequency(p),a=progress.get(p.questionId || p.practiceQuestionId);
   b.append(node('span',(p.executionReady?'Graded example tests':p.contentAvailable?'Practice here · ungraded':'External link only')+(f>=0?' · frequency '+f+'%':'')+(a?' · '+(a==='passed'?'Passed supplied tests':'Attempted here'):''),'small'));b.onclick=()=>{showView('solve');void open(p);};list.append(b);
  }
  if(!results.length)list.append(node('p','No matching problems. Try fewer filters.','small'));
  $('catalogPage').textContent='Page '+(page+1)+' of '+Math.max(1,Math.ceil(results.length/SIZE));$('catalogPrev').disabled=page===0;$('catalogNext').disabled=(page+1)*SIZE>=results.length;
 }
 async function open(p,linkEditor=true){
  if(busy){$('coachAdvice').textContent='Finish or stop the current run before selecting another problem.';return;}selected=p.slug;if(linkEditor)window.dispatchEvent(new CustomEvent('cacm:selection-pending',{detail:{title:p.title}}));render();$('catalogDetail').hidden=false;const current=++version,box=$('catalogDetail');box.replaceChildren(node('p','Loading problem…'));
  try{
   let d;
   if(p.contentAvailable){try{const r=await fetch('./data/problem-details/'+encodeURIComponent(p.slug)+'.json',{signal:AbortSignal.timeout(15000)});if(!r.ok)throw Error('Unavailable');d=await r.json();await PracticeDB.set('problem-detail:'+p.slug,d);}catch{d=await PracticeDB.get('problem-detail:'+p.slug);if(!d && p.executionReady){const r=await fetch('./data/questions.json');const bank=await r.json();const q=bank.questions.find(q=>q.id===p.questionId);if(q)d={description:q.description,constraints:q.constraints,examples:[],starterCode:q.starterCode,hints:[q.hint]};}if(!d)throw Error('Open this problem once with the server available to cache its text.');}}
   if(current!==version)return;box.replaceChildren(node('h3',p.title));const tags=node('div',undefined,'catalog-tags');[p.difficulty,...p.topics.slice(0,5)].forEach(t=>tags.append(node('span',t,'pill')));box.append(tags,link(p.sourceUrl,'Open original on LeetCode'));
   if(p.executionReady){const b=node('button','Focus Python editor');b.id='catalogSolve';b.type='button';b.onclick=()=>window.dispatchEvent(new CustomEvent('cacm:open-problem',{detail:{questionId:p.questionId,focus:true}}));box.append(b,node('p','Runs supplied visible examples, not LeetCode hidden tests.','small'));}
   else box.append(node('p',d?.practiceNote || 'No matching statement is available. Open the original link.','note'));
   if (linkEditor && p.executionReady) {
     activeQuestionId=p.questionId;window.dispatchEvent(new CustomEvent('cacm:open-problem',{detail:{questionId:p.questionId}}));
   } else if(linkEditor && d?.practiceQuestion) {
     activeQuestionId=d.practiceQuestion.id;window.dispatchEvent(new CustomEvent('cacm:open-problem',{detail:{questionId:d.practiceQuestion.id,question:d.practiceQuestion}}));
     const focus=node('button','Focus Python editor');focus.onclick=()=>document.getElementById('code').focus();box.append(focus);
   }
   if(linkEditor && !p.contentAvailable)window.dispatchEvent(new CustomEvent('cacm:external-only',{detail:{title:p.title}}));
   if(d){box.append(node('p',d.description,'catalog-copy'));if(d.constraints?.length){box.append(node('h4','Constraints'));const ul=node('ul');d.constraints.forEach(c=>ul.append(node('li',c)));box.append(ul);}for(const [i,e] of (d.examples||[]).entries())box.append(node('h4','Example '+(i+1)),node('pre',e.text));if(d.starterCode){const s=node('details');s.append(node('summary','Original Python starter template'),node('pre',d.starterCode));box.append(s);}if(d.hints?.length){const s=node('details');s.append(node('summary','Hints'));d.hints.forEach(h=>s.append(node('p',h)));box.append(s);}}
   const companies=Object.keys(p.companies);if(companies.length){const s=node('details');s.append(node('summary','Reported company associations ('+companies.length+')'),node('p',companies.join(', ')));box.append(s);}
  }catch(e){if(current===version)box.replaceChildren(node('h3',p.title),node('p',e.message,'catalog-error'),link(p.sourceUrl,'Open on LeetCode'));}
 }
 async function init(){try{const r=await fetch('./data/problem-catalog.json');if(!r.ok)throw Error('Catalog file missing.');data=await r.json();items=data.problems;[...new Set(items.flatMap(p=>p.topics))].sort().forEach(t=>$('catalogTopic').add(new Option(t,t)));[...new Set(items.flatMap(p=>Object.keys(p.companies)))].sort().forEach(c=>$('catalogCompany').add(new Option(c,c)));for(const id of ['catalogSearch','catalogDifficulty','catalogTopic','catalogCompany','catalogPeriod','catalogReady','catalogProgress','catalogSort'])$(id).addEventListener(id==='catalogSearch'?'input':'change',filter);$('catalogPrev').onclick=()=>{page--;render();};$('catalogNext').onclick=()=>{page++;render();};const routedTopic=new URLSearchParams(location.search).get('topic');if(routedTopic){const plan=StudyCoach.parse(routedTopic,[...$('catalogCompany').options].map(o=>o.value).filter(Boolean),[...$('catalogTopic').options].map(o=>o.value).filter(Boolean));$('catalogTopic').value=plan.topic;$('catalogCompany').value=plan.company;$('catalogDifficulty').value=plan.difficulty;$('coachWish').value=routedTopic;}filter(false);if(window.CACM_WORKSPACE_READY && results.length)void open(items.find(p=>(p.questionId||p.practiceQuestionId)===activeQuestionId)||results[0]);}catch(e){$('catalogCount').textContent='Catalog unavailable';$('catalogNote').textContent=e.message;}}
 window.addEventListener('cacm:attempts',({detail})=>{attempts=detail.attempts;progress=new Map();for(const a of detail.attempts)if(!progress.has(a.questionId))progress.set(a.questionId,(a.serverResult||a.result)?.status||'attempted');filter(false);});
 window.addEventListener('cacm:workspace-ready',()=>{try{$('coachWish').value=localStorage.getItem('cacm.coachWish:'+($('userId').value||'student_1'))||'';}catch{}if(results.length && !selected)void open(items.find(p=>(p.questionId||p.practiceQuestionId)===activeQuestionId)||results[0]);});
 window.addEventListener('cacm:problem-loaded',({detail})=>{
   activeQuestionId=detail.questionId;
   const p=items.find(p=>(p.questionId||p.practiceQuestionId)===detail.questionId);
   if(p){$('bankProblem').hidden=true;if(p.slug!==selected)void open(p,false);}
   else if(window.CACM_WORKSPACE_READY){selected='';$('catalogDetail').hidden=true;$('bankProblem').hidden=$('source').value==='custom';}
 });
 window.addEventListener('cacm:run-state',({detail})=>{busy=detail.busy;for(const id of ['catalogSearch','catalogDifficulty','catalogTopic','catalogCompany','catalogPeriod','catalogReady','catalogProgress','catalogSort','coachWish','coachNext'])$(id).disabled=busy;});
 window.addEventListener('cacm:run-completed',({detail})=>{
   const r=detail.attempt.result;
   $('coachAdvice').textContent=r.status==='passed'?'Supplied tests passed. Choose Suggest next problem to continue.':r.status==='unverified'?'Outputs observed only. No correctness or mastery claim is made.':('Result: '+r.status.replaceAll('_',' ')+'. Inspect the diagnostic, edit your code and retry.');
 });
 function showView(view){
   const solving=view==='solve';
   document.querySelector('.catalog-section').hidden=solving;
   $('codingWorkspace').hidden=!solving;
   $('browseProblems').setAttribute('aria-pressed',String(!solving));
   $('solveProblem').setAttribute('aria-pressed',String(solving));
 }
 function setup(){
   const section=document.querySelector('.catalog-section'),workspace=$('codingWorkspace');
   const problemPanel=workspace.querySelector('.problem');problemPanel.prepend($('catalogDetail'));
   const navigation=node('div',undefined,'workspace-navigation');
   const browse=node('button','Browse problems','secondary');browse.id='browseProblems';browse.type='button';browse.onclick=()=>showView('browse');
   const solve=node('button','Python workspace','secondary');solve.id='solveProblem';solve.type='button';solve.onclick=()=>showView('solve');
   navigation.append(browse,solve);section.before(navigation);
   const filters=document.querySelector('.catalog-filters'),more=node('details',undefined,'more-filters');more.append(node('summary','More filters'));
   const extra=node('div',undefined,'extra-filter-grid');
   for(const id of ['catalogPeriod','catalogReady','catalogProgress','catalogSort'])extra.append($(id).closest('label'));
   more.append(extra);filters.after(more);
   const settings=node('details',undefined,'page-settings');settings.append(node('summary','Student, course & offline settings'));const toolbar=document.querySelector('.toolbar');toolbar.before(settings);settings.append(toolbar);
   const records=node('details',undefined,'practice-records');records.append(node('summary','My progress & attempt history'));const lower=document.querySelector('.lower');lower.before(records);records.append(lower);
   const tools=node('details',undefined,'editor-tools');tools.append(node('summary','Editor tools & optional AI'));tools.append($('resetProblem'),$('errorExample'),$('explain').closest('.actions'),$('aiConfig'),$('aiResult'));workspace.querySelector('.editor').append(tools);
   const inputs=node('details');inputs.append(node('summary','Test inputs'));const inputBox=$('practiceInputsBox');inputBox.prepend(inputs);while(inputBox.children.length>1)inputs.append(inputBox.children[1]);
   showView('browse');
   const advanced=node('details');advanced.id='legacyProblemChooser';advanced.append(node('summary','Other practice bank or custom input'));
   const sourceLabel=$('source').closest('label');advanced.append(sourceLabel,$('bankLabel'));problemPanel.append(advanced);
   $('coachForm').onsubmit=event=>{
     event.preventDefault();if(!data)return;
     try{localStorage.setItem('cacm.coachWish:'+($('userId').value || 'student_1'),$('coachWish').value);}catch{}
     const plan=StudyCoach.parse($('coachWish').value,[...$('catalogCompany').options].map(o=>o.value).filter(Boolean),[...$('catalogTopic').options].map(o=>o.value).filter(Boolean));
     $('catalogCompany').value=plan.company;$('catalogTopic').value=plan.topic;$('catalogDifficulty').value=plan.difficulty;
     $('catalogSearch').value='';$('catalogReady').value='';$('catalogProgress').value='';$('catalogSort').value=plan.company?'frequency':'title';
     selected='';filter();
     $('coachAdvice').textContent='Practice request: '+[plan.company,plan.difficulty,plan.topic].filter(Boolean).join(' · ')+'. '+results.length+' matching problems. Adjust filters if the request was not understood.';
   };
   $('coachNext').onclick=()=>{
     if(busy)return;
     const eligible=results.map(p=>({...p,questionId:p.questionId || p.practiceQuestionId}));
     const decision=StudyCoach.recommend(eligible,attempts,activeQuestionId);$('coachAdvice').textContent=decision.reason;
     if(decision.slug){const p=results.find(p=>p.slug===decision.slug);if(p){showView('solve');void open(p);}}
     else if(decision.action==='retry'){showView('solve');$('code').focus();}
   };
   void init();
 }
 document.addEventListener('DOMContentLoaded',setup);
})();
