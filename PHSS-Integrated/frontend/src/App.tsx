import { CourseDashboard } from './CourseDashboard';
import { requestWord, saveDownload } from './reportDownload';
import { LessonChoice, VideoProgressSummary } from './RecommendedLesson';
import { CacmPanel, RoutedResult } from './IntegratedTools';
import { useEffect, useState, type FormEvent } from 'react';
import { BookOpen, Code2, Search, Sparkles, GraduationCap, LogOut, ArrowUpRight, LoaderCircle, ShieldCheck, Send, RefreshCw, RotateCcw, Table, LayoutGrid } from 'lucide-react';

type User = { userId: string; name: string; email: string; role?: string };
type Tab = 'assistant' | 'learning' | 'research' | 'coding';
const API = '';
async function api<T=any>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(API + path, { credentials: 'same-origin', ...init, headers: { 'Content-Type': 'application/json' } });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || data.detail || `Request failed (${response.status})`);
  return data as T;
}
export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [authMode, setAuthMode] = useState<'login'|'register'|'forgot'>('login');
  const [authForm, setAuthForm] = useState({ name: '', email: '', password: '' });
  const [tab, setTab] = useState<Tab>('assistant');
  const [topic, setTopic] = useState('');
  const [message, setMessage] = useState('');
  const [count, setCount] = useState(5);
  const [level, setLevel] = useState('');
  const [codingView,setCodingView]=useState<'review'|'practice'>('review');
  const [codingRequest,setCodingRequest]=useState('');
  const [handoffContext, setHandoffContext] = useState<any>({});
  const [viewingByTopic,setViewingByTopic] = useState<Record<string,number>>({});
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [result, setResult] = useState<any>(null);
  const [aiHealth, setAiHealth] = useState<'checking'|'ready'|'offline'>('checking');
  const [journeys, setJourneys] = useState<any[]>([]);
  const [coursesLoading,setCoursesLoading]=useState(false);
  const [coursesError,setCoursesError]=useState('');
  const [existingRoadmapPrompt, setExistingRoadmapPrompt] = useState<any>(null);

  useEffect(() => {
    api<{ user: User }>('/api/auth/me').then(d => setUser(d.user)).catch(() => setUser(null));
    api('/api/ai/health').then(() => setAiHealth('ready')).catch(() => setAiHealth('offline'));
    if(user){setCoursesLoading(true);setCoursesError('');api<{ journeys: any[] }>('/api/ai/learning/journeys').then(d => setJourneys(d.journeys||[])).catch(e=>setCoursesError(e.message)).finally(()=>setCoursesLoading(false));}
  }, [tab,user?.userId]);

  useEffect(()=>{
    const receive=(e:Event)=>setHandoffContext((v:any)=>({...v,research:(e as CustomEvent).detail}));
    window.addEventListener('phss:research-context',receive);
    return ()=>window.removeEventListener('phss:research-context',receive);
  },[]);
  useEffect(()=>{const refresh=()=>api<{journeys:any[]}>('/api/ai/learning/journeys').then(d=>setJourneys(d.journeys||[])).catch(()=>{});window.addEventListener('phss:learning-progress',refresh);return()=>window.removeEventListener('phss:learning-progress',refresh);},[user?.userId]);
  useEffect(()=>{if(!user)return;const refresh=()=>api('/api/learning/video-progress').then(d=>{const counts:Record<string,number>={};for(const r of d.progress||[])if(r.completed)counts[r.topic]=(counts[r.topic]||0)+1;setViewingByTopic(counts);}).catch(()=>{});refresh();window.addEventListener('phss:video-progress',refresh);return()=>window.removeEventListener('phss:video-progress',refresh);},[user?.userId]);
  useEffect(()=>{if(tab!=='assistant')window.scrollTo({top:0,behavior:'auto'});},[tab,result]);
  function updateAuth(key: keyof typeof authForm, value: string) { setAuthForm(v => ({...v, [key]: value})); }
  async function submitAuth(e: FormEvent) {
    e.preventDefault(); setBusy(true); setError(''); setNotice('');
    try {
      if (authMode === 'forgot') { const r = await api('/api/auth/forgot-password', {method:'POST', body:JSON.stringify({email:authForm.email})}); setNotice(r.message || 'If an account exists, a reset link will be sent.'); }
      else if (authMode === 'register') { const r = await api('/api/auth/register', {method:'POST', body:JSON.stringify(authForm)}); setNotice(r.message || 'Check your email to verify your account.'); setAuthMode('login'); }
      else { const r = await api<{user:User}>('/api/auth/login', {method:'POST', body:JSON.stringify({email:authForm.email,password:authForm.password})}); setJourneys([]); setCoursesError(''); setUser(r.user); setNotice(''); api('/api/ai/health').then(() => setAiHealth('ready')).catch(() => setAiHealth('offline')); }
    } catch (e:any) { setError(e.message); } finally { setBusy(false); }
  }
  async function runAgent(path: string, body: object) {
    setBusy(true); setError(''); setNotice(''); setResult(null); setExistingRoadmapPrompt(null);
    const submitted=String((body as any).message||'');
    if(path==='/api/ai/orchestrate'){
      if(/```|\b(?:print|input)\s*\(|(?:^|\n)\s*(?:def |class |import |from |for |while |if |[a-zA-Z_]\w*\s*=)/.test(submitted)){setTab('coding');setCodingView('review');}
      else if(/\b(practice|practise|questions?|problems?|interview)\b/i.test(submitted)&&/\b(amazon|google|microsoft|leetcode|coding|dsa|meta|infosys|tcs)\b/i.test(submitted)){setTab('coding');setCodingView('practice');setCodingRequest(submitted);}
      else if(/\b(learn|teach|study|roadmap|understand|trees)\b/i.test(submitted))setTab('learning');
    }

    try {
      const r = await api<any>(path, {method:'POST', body:JSON.stringify(path==='/api/ai/orchestrate'?{...body,context:{from:tab,current_level:level||undefined,...(body as any).context}}:body)});
      const routed=r.result??r;
      const first=routed.agent_results?.[0];
      if(path==='/api/ai/orchestrate' && first && ['learning','coding','research'].includes(first.agent)){
        setTab(first.agent);
        requestAnimationFrame(()=>document.querySelector('.work-card:not(.home-search)')?.scrollIntoView({behavior:'smooth',block:'start'}));
        if(first.success===false)setError(first.message||'The requested workspace could not generate a result. Please try again.');
        if(first.agent==='coding'){
          setCodingView(first.practice_request?'practice':'review');
          if(first.practice_request)setCodingRequest(first.practice_request);
        }
        if(first.agent==='learning'&&first.plan){setResult(routed.agent_results.length===1?{plan:first.plan}:routed);setTopic(first.plan.topic||routed.topic);setHandoffContext({topic:first.plan.topic||routed.topic});return;}
        if(first.agent==='research'&&first.research){setResult({research:first.research});setTopic(routed.topic);return;}
      }
      const readyPlan=r.existing_roadmap?.existing_plan||r.existing_plan||r.plan;
      if(readyPlan?.steps){
        setResult({plan:readyPlan});setTopic(readyPlan.topic);setTab('learning');
      }else{
        setResult(r.result??r.research??r.feedback??r);
        if(r.result?.topic)setTopic(r.result.topic);
      }
      api<{ journeys: any[] }>('/api/ai/learning/journeys').then(d => { if (d?.journeys) setJourneys(d.journeys); }).catch(() => {});
    } catch(e:any) { setError(e.message); } finally { setBusy(false); }
  }
  function handoff(agent: string, request: string, nextTopic: string) {
    const context = {...handoffContext, from:tab, topic:nextTopic, previous_result:JSON.stringify(result).slice(0,14000)};
    setHandoffContext(context);setTopic(nextTopic);setMessage(request);setTab(agent as Tab);
    if (agent === 'learning') {
      runAgent('/api/ai/learning/plan',{topic:nextTopic,current_level:level,goal:request.slice(0,500)});
    } else {
      runAgent('/api/ai/orchestrate',{message:request,mode:agent,context});
    }
  }
  function switchTab(newTab: Tab) {
    setTab(newTab);
    setError('');
    const routedPlan = result?.agent_results?.find((r:any)=>r.agent==='learning' && r.plan)?.plan;
    if (newTab === 'learning' && routedPlan) {
      setResult({plan:routedPlan});
      if(routedPlan.topic)setTopic(routedPlan.topic);
    } else if (newTab === 'learning' && result?.plan) {
      if (result.plan.topic) setTopic(result.plan.topic);
    } else if (newTab !== 'learning' && !(newTab === 'assistant' && result?.plan)) {
      setResult(null);
    }
  }

  async function logout() { try { await api('/api/auth/logout',{method:'POST'}); } finally { setUser(null); setJourneys([]); setCoursesError(''); setResult(null); setTab('assistant'); } }
  if (!user) return <main className="auth-shell"><section className="auth-brand"><div className="brand-mark"><GraduationCap size={28}/></div><p className="eyebrow">PERSONALIZED HYBRID STUDY SYSTEM</p><h1>Learn with a system that adapts to you.</h1><p className="muted big">One study space for learning, coding practice, and evidence-led research.</p><div className="auth-points"><span><BookOpen size={17}/> Personalized learning paths</span><span><Code2 size={17}/> Coding practice and feedback</span><span><Search size={17}/> Research-paper discovery</span></div></section><section className="auth-card"><p className="eyebrow">YOUR STUDY WORKSPACE</p><h2>{authMode==='login'?'Welcome back':authMode==='register'?'Create your account':'Reset your password'}</h2><p className="muted">{authMode==='login'?'Sign in to continue your progress.':authMode==='register'?'Create an account to start your learning journey.':'We will email a reset link if the account exists.'}</p><form onSubmit={submitAuth} className="stack">{authMode==='register'&&<label>Full name<input required minLength={2} value={authForm.name} onChange={e=>updateAuth('name',e.target.value)} autoComplete="name"/></label>}<label>Email address<input required type="email" value={authForm.email} onChange={e=>updateAuth('email',e.target.value)} autoComplete="email"/></label>{authMode!=='forgot'&&<label>Password<input required type="password" minLength={authMode==='register'?12:1} value={authForm.password} onChange={e=>updateAuth('password',e.target.value)} autoComplete={authMode==='register'?'new-password':'current-password'}/>{authMode==='register'&&<small>Use at least 12 characters.</small>}</label>}<button className="primary" disabled={busy}>{busy?<LoaderCircle className="spin" size={17}/>:null}{authMode==='login'?'Sign in':authMode==='register'?'Create account':'Send reset link'}</button></form>{error&&<p className="message error">{error}</p>}{notice&&<p className="message success">{notice}</p>}<div className="auth-links">{authMode==='login'?<><button className="text-button" onClick={()=>setAuthMode('register')}>Create an account</button><button className="text-button" onClick={()=>setAuthMode('forgot')}>Forgot password?</button></>:<button className="text-button" onClick={()=>{setAuthMode('login');setError('');setNotice('')}}>Back to sign in</button>}</div><p className="fine-print"><ShieldCheck size={14}/> Your account and study progress are protected.</p><p className="fine-print">Use your registered email to verify your account or reset your password.</p></section></main>;
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark small"><GraduationCap size={21}/></div><div><strong>PHSS</strong><small>Study system</small></div></div>
        <div className="sidebar-label">WORKSPACE</div>
        <nav>{([{id:'assistant',label:'AI Assistant',icon:Sparkles},{id:'learning',label:'Learning Agent',icon:BookOpen},{id:'coding',label:'Coding Agent',icon:Code2},{id:'research',label:'Research Agent',icon:Search}] as const).map(item=><button key={item.id} className={`nav-item ${tab===item.id?'active':''}`} onClick={()=>switchTab(item.id)}><item.icon size={18}/>{item.label}</button>)}</nav>
        <div className="sidebar-bottom">
          <div className="status-pill"><span className={`status-dot ${aiHealth==='ready'?'green':aiHealth==='offline'?'red':''}`}/>{aiHealth==='ready'?'Assistant available':aiHealth==='offline'?'Assistant unavailable':'Checking availability'}</div>
          
          <button className="nav-item" onClick={logout}><LogOut size={17}/> Sign out</button>
          <div className="user-mini"><div className="avatar">{user.name.slice(0,1).toUpperCase()}</div><div><strong>{user.name}</strong><small>{user.email}</small></div></div>
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <div><p className="eyebrow">YOUR PERSONAL STUDY SPACE</p><h1>{tab==='assistant'?'AI study assistant':tab==='learning'?'Learning workspace':tab==='coding'?'Coding workspace':'Research workspace'}</h1></div>
          <div className="top-actions"><span className="online"><span className="status-dot green"/> Signed in</span><button className="icon-button" title="Refresh status" onClick={()=>api('/api/ai/health').then(()=>setAiHealth('ready')).catch(()=>setAiHealth('offline'))}><RefreshCw size={17}/></button></div>
        </header>
        {tab==='assistant'&&<section className="home-search work-card"><p className="eyebrow">STUDY ASSISTANT</p><h2>What would you like to work on?</h2>{tab==='assistant'&&<form className="stack" onSubmit={(e: FormEvent)=>{e.preventDefault();runAgent('/api/ai/orchestrate',{message,mode:'auto',context:{}})}}><label>What would you like help with?<textarea rows={3} placeholder="Ask a question, explore a topic, or paste your code…" spellCheck={false} style={{fontFamily:/```|\b(?:def|print|input)\s*\(/.test(message)?"monospace":"inherit",whiteSpace:"pre-wrap",tabSize:4}} value={message} onChange={e=>setMessage(e.target.value)}/></label><label className="optional-level">Learning level (optional)<select value={level} onChange={e=>setLevel(e.target.value)}><option value="">Automatic</option><option value="beginner">Beginner</option><option value="intermediate">Intermediate</option><option value="advanced">Advanced</option></select></label><button className="primary" disabled={busy||!message.trim()}>{busy?<LoaderCircle className="spin" size={17}/>:<Send size={17}/>} Ask PHSS</button></form>}</section>}

        {tab==='assistant'&&<CourseDashboard courses={journeys} loading={coursesLoading} error={coursesError} onExplore={()=>{}} onResume={c=>{setTab('learning');setTopic(c.topic_title);setResult({plan:c.plan});}}/>}
        {tab!=='assistant'&&!result&&!busy&&<section className="cross-agent-bar"><form onSubmit={(e:FormEvent)=>{e.preventDefault();setTab('assistant');runAgent('/api/ai/orchestrate',{message,mode:'auto',context:{...handoffContext,from:tab,topic,previous_result:JSON.stringify(result).slice(0,14000)}})}}><label>Ask a follow-up<textarea rows={3} spellCheck={false} required maxLength={2000} value={message} onChange={e=>setMessage(e.target.value)} placeholder="Ask a doubt or paste code here; keep its line breaks and indentation."/></label><button className="primary" disabled={busy}>Ask PHSS →</button></form><div className="handoff-actions"><button className="text-button" disabled={busy} onClick={()=>handoff('learning','Explain '+topic+' in the context of my current work',topic)}>Learn this topic</button><button className="text-button" disabled={busy} onClick={()=>handoff('coding','Help me implement '+topic,topic)}>Code this topic</button></div></section>}


        {(tab!=='assistant'||result||error||existingRoadmapPrompt)&&<section className="work-card">
          <div className="work-heading">
            <div>
              <p className="eyebrow">{tab==='assistant'?'YOUR STUDY ASSISTANT':tab==='learning'?'PERSONALIZED LEARNING':tab==='research'?'ACADEMIC DISCOVERY':'CODING PRACTICE'}</p>
              <h2>{tab==='assistant'?'Your results':tab==='learning'?'Your learning roadmap':tab==='research'?'Search academic papers':'Coding practice and review'}</h2>
              <p className="muted">{tab==='assistant'?'Continue with the explanations, practice or research below.':tab==='learning'?'Follow your roadmap, choose reading or video lessons, and check your understanding.':tab==='research'?'Find relevant papers, compare findings, and download your research report.':'Practice interview problems, review your code, and work on the concepts you need.'}</p>
            </div>
          </div>

          {tab === 'learning' ? (
            <div className="learning-workspace-grid">
              {busy&&<p role="status" className="workspace-loading"><LoaderCircle className="spin" size={20}/> Preparing your learning modules…</p>}


              <div className="learning-main-content">
                <div className="learning-level-toolbar"><label>Learning level (optional)<select value={level} onChange={e=>setLevel(e.target.value)}><option value="">Automatic</option><option value="beginner">Beginner</option><option value="intermediate">Intermediate</option><option value="advanced">Advanced</option></select></label><button type="button" className="secondary" disabled={busy||!topic.trim()} onClick={()=>runAgent('/api/ai/learning/plan',{topic,current_level:level||'beginner',goal:'Learn '+topic,force_new:true})}>Update roadmap for this level</button></div>

                {!busy&&!(result?.plan?.steps||result?.steps||result?.agent_results?.some((a:any)=>a.plan?.steps))&&<div className="learning-form-card">
                  <form onSubmit={(e: FormEvent)=>{e.preventDefault();runAgent('/api/ai/learning/plan',{topic,current_level:level,goal:`Build a personalized learning path for ${topic}`})}}>
                    <label>What do you want to learn?
                      <input
                        value={topic}
                        onChange={e=>setTopic(e.target.value)}
                        required
                        maxLength={250}
                        placeholder="e.g. Trees in Data Structures and Algorithms, Python Asyncio..."
                      />
                    </label>
                    <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end', flexWrap: 'wrap', marginTop: 12 }}>

                      <button className="primary" style={{ minWidth: 210, height: 44 }} disabled={busy||!topic.trim()}>
                        {busy?<LoaderCircle className="spin" size={17}/>:<BookOpen size={17}/>} Generate learning path
                      </button>
                    </div>
                  </form>
                  <div className="topic-chips">
                    <span style={{ fontSize: 11, fontWeight: 700, color: '#64748b' }}>💡 Quick Suggestions:</span>
                    {[
                      { label: '🌳 Trees in DSA', q: 'Trees in Data Structures and Algorithms' },
                      { label: '⚡ Python Asyncio', q: 'Master Asynchronous Programming in Python' },
                      { label: '📊 Dynamic Programming', q: 'Dynamic Programming Patterns' },
                      { label: '🌐 REST APIs', q: 'Building REST APIs with FastAPI' }
                    ].map(chip => (
                      <button
                        key={chip.label}
                        type="button"
                        className="topic-chip-btn"
                        onClick={() => {
                          setTopic(chip.q);
                          runAgent('/api/ai/learning/plan', {
                            topic: chip.q,
                            current_level: 'beginner',
                            goal: `Build a personalized learning path for ${chip.q}`
                          });
                        }}
                      >
                        {chip.label}
                      </button>
                    ))}
                  </div>
                </div>}

                {existingRoadmapPrompt && (
                  <div className="existing-roadmap-card">
                    <div className="existing-roadmap-header">
                      <div className="existing-icon-box"><BookOpen size={24} /></div>
                      <div>
                        <span className="badge badge-concept">Existing Roadmap Detected</span>
                        <h3>{existingRoadmapPrompt.existing_topic}</h3>
                        <p className="muted" style={{ margin: '4px 0 0', fontSize: 13 }}>
                          You already have an active roadmap with <strong>{existingRoadmapPrompt.existing_mastery}% mastery</strong> ({existingRoadmapPrompt.existing_completed}/{existingRoadmapPrompt.existing_total} concepts mastered).
                        </p>
                      </div>
                    </div>

                    <p style={{ margin: '14px 0 6px', fontSize: 13, color: '#334155' }}>
                      Would you like to continue your existing progress or build a fresh roadmap from scratch?
                    </p>

                    <div className="existing-roadmap-actions">
                      <button
                        type="button"
                        className="primary"
                        onClick={() => {
                          setTopic(existingRoadmapPrompt.existing_topic);
                          setResult({ plan: existingRoadmapPrompt.existing_plan });
                          setExistingRoadmapPrompt(null);
                        }}
                      >
                        <RotateCcw size={16} /> Resume Existing Roadmap ({existingRoadmapPrompt.existing_mastery}% Mastery)
                      </button>
                      <button
                        type="button"
                        className="secondary"
                        onClick={() => {
                          const requestedTopic = existingRoadmapPrompt.topic || topic;
                          setExistingRoadmapPrompt(null);
                          runAgent('/api/ai/learning/plan', {
                            topic: requestedTopic,
                            current_level: 'beginner',
                            goal: `Build a personalized learning path for ${requestedTopic}`,
                            force_new: true,
                          });
                        }}
                      >
                        <Sparkles size={16} /> Create Brand New Roadmap
                      </button>
                    </div>
                  </div>
                )}

                {error&&<p className="message error">{error}</p>}
                {notice&&<p className="message success">{notice}</p>}
                {result&&<ResultView onHandoff={handoff} result={result?.agent_results?.find((r:any)=>r.agent==='learning' && r.plan)?.plan ? {plan:result.agent_results.find((r:any)=>r.agent==='learning' && r.plan).plan} : result}/>}
              </div>
            </div>
          ) : (
            <>
              {existingRoadmapPrompt && (
                <div className="existing-roadmap-card" style={{ marginTop: 16 }}>
                  <div className="existing-roadmap-header">
                    <div className="existing-icon-box"><BookOpen size={24} /></div>
                    <div>
                      <span className="badge badge-concept">Existing Roadmap Detected</span>
                      <h3>{existingRoadmapPrompt.existing_topic}</h3>
                      <p className="muted" style={{ margin: '4px 0 0', fontSize: 13 }}>
                        You already have an active roadmap with <strong>{existingRoadmapPrompt.existing_mastery}% mastery</strong> ({existingRoadmapPrompt.existing_completed}/{existingRoadmapPrompt.existing_total} concepts mastered).
                      </p>
                    </div>
                  </div>
                  <div className="existing-roadmap-actions">
                    <button
                      type="button"
                      className="primary"
                      onClick={() => {
                        setTopic(existingRoadmapPrompt.existing_topic);
                        setResult({ plan: existingRoadmapPrompt.existing_plan });
                        setExistingRoadmapPrompt(null);
                      }}
                    >
                      <RotateCcw size={16} /> Resume Existing Roadmap ({existingRoadmapPrompt.existing_mastery}% Mastery)
                    </button>
                    <button
                      type="button"
                      className="secondary"
                      onClick={() => {
                        const requestedTopic = existingRoadmapPrompt.topic || topic;
                        setExistingRoadmapPrompt(null);
                        runAgent('/api/ai/learning/plan', {
                          topic: requestedTopic,
                          current_level: 'beginner',
                          goal: `Build a personalized learning path for ${requestedTopic}`,
                          force_new: true,
                        });
                      }}
                    >
                      <Sparkles size={16} /> Create Brand New Roadmap
                    </button>
                  </div>
                </div>
              )}
              {tab==='research'&&(
                <form className="stack" onSubmit={async(e: FormEvent)=>{
                  e.preventDefault();
                  if (!topic.trim()) return;
                  setBusy(true); setError('');
                  try {
                    const r = await api('/api/research/jobs', { method: 'POST', body: JSON.stringify({ topic, count }) });
                    setResult({ researchJob: r.jobId, topic, count, phase: 'starting' });
                  } catch (err: any) {
                    setError(err.message);
                  } finally {
                    setBusy(false);
                  }
                }}>
                  <label>
                    Research topic
                    <input value={topic} onChange={e=>setTopic(e.target.value)} required maxLength={300} placeholder="Example: PCB defect detection using deep learning"/>
                  </label>
                  <label>
                    Number of papers to analyze
                    <select value={count} onChange={e=>setCount(Number(e.target.value))}>
                      <option value={3}>3 papers</option>
                      <option value={5}>5 papers (Recommended)</option>
                      <option value={10}>10 papers (Comprehensive)</option>
                    </select>
                  </label>
                  <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginTop: '8px' }}>
                    <button className="primary" disabled={busy || !topic.trim()} type="submit">
                      {busy ? <LoaderCircle className="spin" size={17}/> : <Search size={17}/>} Start Full Literature Review (PHSS Research Agent)
                    </button>
                    <button type="button" className="secondary" disabled={busy || !topic.trim()} onClick={()=>runAgent('/api/ai/research/search', { topic, count })}>
                      Fast Search & Relevance Ranking
                    </button>
                    <a href="/research/" target="_blank" rel="noreferrer" className="secondary link-button" style={{ padding: '12px 16px', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                      Open Dedicated Research Workspace <ArrowUpRight size={15}/>
                    </a>
                  </div>
                  <p className="fine-print">
                    Your report brings together paper comparisons, limitations, candidate research gaps, and a downloadable Word document.
                  </p>
                </form>
              )}
              {tab==='coding'&&<div className="coding-mode-tabs" role="group" aria-label="Coding task"><button className={codingView==='review'?'primary':'secondary'} onClick={()=>setCodingView('review')}>Code review</button><button className={codingView==='practice'?'primary':'secondary'} onClick={()=>setCodingView('practice')}>Interview practice</button></div>}
              {tab==='coding'&&codingView==='review'&&!result&&!busy&&<p>Paste your code in the search box above and choose Ask PHSS to review it.</p>}
              {tab==='coding'&&codingView==='practice'&&<div className="coding-launch"><iframe title="Interview preparation and coding practice" src={'/coding/?topic='+encodeURIComponent(codingRequest||topic)} style={{width:'100%',height:'75vh',border:0,borderRadius:12}}/><div className="coding-preview"><Code2 size={36}/><div><strong>Interview practice</strong><p className="muted">Choose a problem, run your solution, and review your saved attempts.</p></div></div><a className="primary link-button" href={'/coding/?topic='+encodeURIComponent(codingRequest||topic)} target="_blank" rel="noreferrer">Open coding workspace <ArrowUpRight size={17}/></a><p className="fine-print">Your practice history helps you find topics to review.</p></div>}
              {error&&<p className="message error">{error}</p>}
              {notice&&<p className="message success">{notice}</p>}
              {busy&&<p className="workspace-loading" role="status"><LoaderCircle className="spin" size={20}/> {tab==='coding'?(codingView==='review'?'Reviewing your code…':'Opening your practice questions…'):tab==='research'?'Preparing your research…':'Preparing your learning modules…'}</p>}
              {result&&!(tab==='coding'&&codingView==='practice')&&<ResultView onHandoff={handoff} result={result} onSwitchWorkspace={tab==='assistant'?()=>switchTab('learning'):undefined}/>}
            </>
          )}
        </section>}
        <CacmPanel onLearn={t=>handoff('learning','Explain '+t,t)}/><footer>PHSS · Learning, coding and research in one workspace <span>Your progress, saved</span></footer>
      </main>
    </div>
  );
}

function LearningPlanView({ plan, onSwitchWorkspace }: { plan: any; onSwitchWorkspace?: () => void }) {
  const [enrolled,setEnrolled]=useState(false);
  const [enrolling,setEnrolling]=useState(false);
  const [enrollError,setEnrollError]=useState('');
  useEffect(()=>{let active=true;setEnrolled(false);setEnrollError('');api('/api/ai/learning/journeys').then(d=>{if(active)setEnrolled((d.journeys||[]).some((c:any)=>c.topic_title===plan.topic));}).catch(()=>{});return()=>{active=false;};},[plan.topic]);
  async function enroll(){setEnrolling(true);setEnrollError('');try{await api('/api/ai/learning/enroll',{method:'POST',body:JSON.stringify({topic:plan.topic})});setEnrolled(true);window.dispatchEvent(new Event('phss:learning-progress'));}catch(e:any){setEnrollError(e.message);}finally{setEnrolling(false);}}
  const [activeQuizStep, setActiveQuizStep] = useState<any>(null);
  const [quizLoading, setQuizLoading] = useState(false);
  const [quizData, setQuizData] = useState<any>(null);
  const [quizAnswers, setQuizAnswers] = useState<Record<number, number>>({});
  const [descriptiveAnswers, setDescriptiveAnswers] = useState<Record<number, string>>({});
  const [quizSubmitting, setQuizSubmitting] = useState(false);
  const [quizResult, setQuizResult] = useState<any>(null);
  const [quizError, setQuizError] = useState('');
  const [lessonAssessments,setLessonAssessments]=useState<Record<string,any>>(plan.quizProgress?.lessons||{});
  useEffect(()=>{setLessonAssessments(plan.quizProgress?.lessons||{});setActiveQuizStep(null);setQuizData(null);setQuizResult(null);},[plan.topic]);

  async function startQuiz(step: any, forceRefresh = false) {
    if (!forceRefresh && activeQuizStep?.order === step.order && quizData) {
      setActiveQuizStep(null);
      return;
    }
    setActiveQuizStep(step);
    setQuizData(null);
    setQuizResult(null);
    setQuizAnswers({});
    setDescriptiveAnswers({});
    setQuizLoading(true);
    setQuizError('');
    try {
      const res = await api('/api/ai/learning/quiz', {
        method: 'POST',
        body: JSON.stringify({
          current_level: plan.currentLevel||'',
          concept_name: step.concept || step.title,
          resource_url: step.url || '',
          force_refresh: forceRefresh,
        }),
      });
      setQuizData(res.quiz);
    } catch (e: any) {
      setQuizError(e.message || 'Could not load quiz questions.');
    } finally {
      setQuizLoading(false);
    }
  }

  async function submitQuiz() {
    if (!activeQuizStep || !quizData) return;
    setQuizSubmitting(true);
    setQuizError('');
    try {
      const res = await api('/api/ai/learning/quiz/submit', {
        method: 'POST',
        body: JSON.stringify({
          concept_name: activeQuizStep.concept || activeQuizStep.title,
          resource_url: activeQuizStep.url || '',
          attempt_number: quizData.attempt_number || 1,
          answers: quizAnswers,
          descriptive_answers: descriptiveAnswers,
          course_topic: plan.topic,
          lesson_key: String(activeQuizStep.order||'')+':'+String(activeQuizStep.concept||activeQuizStep.title).slice(0,140),
        }),
      });
      setQuizResult(res.evaluation); setLessonAssessments(v=>({...v,[String(activeQuizStep.order||'')+':'+String(activeQuizStep.concept||activeQuizStep.title).slice(0,140)]:{attempted:true,passed:!!res.evaluation.passed,score:res.evaluation.score}})); window.dispatchEvent(new Event('phss:evidence')); window.dispatchEvent(new Event('phss:learning-progress'));
    } catch (e: any) {
      setQuizError(e.message || 'Error submitting quiz.');
    } finally {
      setQuizSubmitting(false);
    }
  }

  const steps = plan.steps || [];

  return (
    <div className="result-panel">
      <div className="enroll-banner"><div><strong>{enrolled?'Your enrolled course':'Roadmap preview'}</strong><p>{enrolled?'Continue learning and pass each lesson quiz.':'Add this roadmap to My courses when you are ready to study.'}</p></div><button className="primary" disabled={enrolled||enrolling} onClick={enroll}>{enrolled?'✓ Enrolled':enrolling?'Enrolling…':'Enroll in course'}</button></div>
      {enrollError&&<p role="alert" className="message error">{enrollError}</p>}

      {onSwitchWorkspace && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#ecfdf5', border: '1px solid #6ee7b7', padding: '10px 14px', borderRadius: 8, marginBottom: 14 }}>
          <span style={{ fontSize: 13, color: '#065f46', fontWeight: 600 }}>
            🧠 Switch to Learning Agent workspace to see the Topics & Progress dashboard!
          </span>
          <button type="button" className="secondary" style={{ padding: '6px 12px', fontSize: 12 }} onClick={onSwitchWorkspace}>
            Open Topics Dashboard <ArrowUpRight size={13} />
          </button>
        </div>
      )}
      <div className="result-head">
        <div>
          <h3>{plan.topic || 'Learning Plan'}</h3>
          {plan.currentLevel && <small className="muted" style={{ display: 'block' }}>Level: {plan.currentLevel}</small>}
        </div>
        <span className="result-count">{steps.length} learning modules</span>
      </div>

      <VideoProgressSummary topic={plan.topic} total={steps.length}/>
      {plan.rationale && (
        <div className="rationale-card">
          <strong>Curriculum Rationale</strong>
          {plan.rationale}
        </div>
      )}

      <div style={{ display: 'grid', gap: '14px', marginTop: '16px' }}>
        {steps.map((s: any) => (
          <div key={s.order || s.title} className="step-item">
            <div className="step-header">
              <div className="step-title-row">
                <span className="step-num">{s.order}</span>
                <strong className="module-title">{s.concept||s.title}</strong>
              </div>
              <div className="step-badges">
                {s.concept && <span className="badge badge-concept">{s.concept}</span>}
                <span className="badge badge-format">{s.format || s.type || 'resource'}</span>
                {s.difficulty && <span className="badge badge-diff">{s.difficulty}</span>}
                {s.estimated_minutes && <span className="badge badge-time">{s.estimated_minutes} min</span>}
              </div>
            </div>

            <p className="step-desc">{s.objective || s.snippet}</p>

            <LessonChoice step={s} topic={plan.topic} level={plan.currentLevel || 'beginner'} assessment={lessonAssessments[String(s.order||'')+':'+String(s.concept||s.title).slice(0,140)]} materials={(plan.resources||steps).filter((r:any)=>(r.target_concept||r.concept)===s.concept&&!/video/i.test(r.format||r.type||''))} onQuiz={v=>startQuiz({...v,order:s.order},true)}/>
            {activeQuizStep?.order === s.order && (
              <div className="quiz-panel">
                {quizLoading && <p><LoaderCircle className="spin" size={15} /> Generating your lesson quiz…</p>}
                {quizError && <p className="message error">{quizError}</p>}
                {quizData?.source_note&&<p className="muted">{quizData.source_note}</p>}
                {quizData && !quizResult && (
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                      <div>
                        <h4 style={{ margin: 0, fontSize: '14px', fontWeight: 700 }}>
                          {quizData.quiz_type === 'adaptive' ? '🎯 Adaptive Retake Assessment' : '🎯 Diagnostic Assessment'}: {quizData.concept_name}
                        </h4>
                        <small className="muted" style={{ fontSize: '11px' }}>
                          {quizData.quiz_type === 'adaptive'
                            ? 'Questions prioritized targeting previously missed concepts, predict output coding, and revision retention.'
                            : String(quizData.questions?.length||0)+' questions · Check your understanding'}
                        </small>
                      </div>
                      <div style={{ display: 'flex', gap: 6 }}>
                        <span className="badge" style={{ background: '#e0e7ff', color: '#4338ca', fontWeight: 700 }}>
                          Attempt #{quizData.attempt_number || 1}
                        </span>
                        {quizData.quiz_type === 'adaptive' && (
                          <span className="badge" style={{ background: '#dcfce7', color: '#166534' }}>
                            Cognitive Adaptive
                          </span>
                        )}
                      </div>
                    </div>

                    {quizData.past_attempts?.length > 0 && (
                      <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 6, padding: '8px 12px', marginBottom: 12, fontSize: 12 }}>
                        <strong>📜 Prior Quiz Attempts:</strong>
                        <ul style={{ margin: '4px 0 0 16px', padding: 0 }}>
                          {quizData.past_attempts.map((pa: any, pIdx: number) => (
                            <li key={pIdx}>
                              Attempt #{pa.attempt_number}: <strong>{Math.round(pa.score * 100)}%</strong> ({pa.correct_count}/{pa.total_questions}) • Status: {pa.passed ? '✅ Passed' : '⚠️ Unresolved'} {pa.weak_areas?.length > 0 && `(Weak in: ${pa.weak_areas.join(', ')})`}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {quizData.questions?.map((q: any) => {
                      const isDescriptive = q.question_type === 'descriptive' || (!q.options || q.options.length === 0);
                      const isCode = q.question_type === 'predict_output' || Boolean(q.code_snippet);
                      const isRevision = Boolean(q.is_revision);

                      return (
                        <div key={q.question_id} className="quiz-q">
                          <div className="quiz-q-title">
                            <span style={{ fontWeight: 800, color: '#17684f', marginRight: 6 }}>Q{q.question_id}:</span>
                            <span>{q.question_text}</span>
                            {isRevision && (
                              <span className="badge" style={{ marginLeft: 6, background: '#dcfce7', color: '#166534' }}>
                                🔄 Revision Retention
                              </span>
                            )}
                            {isCode ? (
                              <span
                                className="badge"
                                style={{
                                  marginLeft: 6,
                                  background: '#ffedd5',
                                  color: '#c2410c',
                                  fontWeight: 700,
                                }}
                              >
                                💻 Predict Code Output
                              </span>
                            ) : isDescriptive ? (
                              <span
                                className="badge"
                                style={{
                                  marginLeft: 6,
                                  background: '#ede9fe',
                                  color: '#6d28d9',
                                }}
                              >
                                Descriptive Explanation
                              </span>
                            ) : (
                              <span
                                className="badge"
                                style={{
                                  marginLeft: 6,
                                  background: '#e0f2fe',
                                  color: '#0369a1',
                                }}
                              >
                                Multiple Choice
                              </span>
                            )}
                          </div>

                          {q.code_snippet && (
                            <pre
                              style={{
                                background: '#0f172a',
                                color: '#38bdf8',
                                padding: '10px 14px',
                                borderRadius: 8,
                                fontSize: 12,
                                fontFamily: 'monospace',
                                overflowX: 'auto',
                                margin: '8px 0 10px',
                                lineHeight: 1.45,
                              }}
                            >
                              <code>{q.code_snippet}</code>
                            </pre>
                          )}

                          {isDescriptive ? (
                            <div style={{ marginTop: 8 }}>
                              <textarea
                                rows={4}
                                className="quiz-textarea"
                                placeholder="Type your answer here in your own words. Explain key structural invariants, operations, or principles..."
                                value={descriptiveAnswers[q.question_id] || ''}
                                onChange={e => setDescriptiveAnswers(prev => ({ ...prev, [q.question_id]: e.target.value }))}
                              />
                              <small style={{ color: '#64748b', fontSize: 11, display: 'block', marginTop: 4 }}>
                                💡 Tip: Answer thoroughly using core technical principles (e.g. BST ordering property, traversal order, height balancing).
                              </small>
                            </div>
                          ) : (
                            <div style={{ marginTop: 6 }}>
                              {q.options?.map((opt: string, optIdx: number) => (
                                <label key={optIdx} className="quiz-opt">
                                  <input
                                    type="radio"
                                    name={`q_${q.question_id}`}
                                    checked={quizAnswers[q.question_id] === optIdx}
                                    onChange={() => setQuizAnswers(prev => ({ ...prev, [q.question_id]: optIdx }))}
                                  />
                                  <span>{opt}</span>
                                </label>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    })}
                    <button
                      type="button"
                      className="primary"
                      disabled={quizSubmitting || (Object.keys(quizAnswers).length === 0 && Object.keys(descriptiveAnswers).length === 0)}
                      onClick={submitQuiz}
                    >
                      {quizSubmitting ? <LoaderCircle className="spin" size={15} /> : null} Submit Quiz Answers (Attempt #{quizData.attempt_number || 1})
                    </button>
                  </div>
                )}

                {quizResult && (
                  <div className="quiz-result">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 8, marginBottom: 8 }}>
                      <div>
                        <strong>Quiz Outcome: {Math.round(quizResult.score * 100)}% ({quizResult.correct_count}/{quizResult.total_questions} points)</strong>
                        <div style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>
                          Attempt #{quizResult.attempt_number || 1} &bull; Type: {quizResult.quiz_type || 'assessment'}
                          {typeof quizResult.prior_mastery === 'number' && typeof quizResult.new_mastery === 'number' && (
                            <span style={{ marginLeft: 8 }}>
                              Mastery: {Math.round(quizResult.prior_mastery * 100)}% &rarr; <strong>{Math.round(quizResult.new_mastery * 100)}%</strong>
                            </span>
                          )}
                        </div>
                      </div>
                      <span className="badge" style={{
                        background: quizResult.passed ? '#dcfce7' : '#fee2e2',
                        color: quizResult.passed ? '#166534' : '#991b1b',
                        padding: '4px 10px',
                        fontSize: 12,
                        fontWeight: 700
                      }}>
                        {quizResult.passed ? '✅ Passed Assessment' : '⚠️ Misconceptions Detected'}
                      </span>
                    </div>

                    {/* Pedagogical Next Action Banner */}
                    {quizResult.next_action && (
                      <div
                        style={{
                          background: quizResult.next_action === 'PROCEED' ? '#ecfdf5' : quizResult.next_action === 'REVISE' ? '#fffbeb' : '#faf5ff',
                          border: `1px solid ${quizResult.next_action === 'PROCEED' ? '#a7f3d0' : quizResult.next_action === 'REVISE' ? '#fde68a' : '#e9d5ff'}`,
                          color: quizResult.next_action === 'PROCEED' ? '#065f46' : quizResult.next_action === 'REVISE' ? '#92400e' : '#6b21a8',
                          padding: '10px 14px',
                          borderRadius: 8,
                          margin: '8px 0 12px',
                          fontSize: 13,
                        }}
                      >
                        <strong>
                          {quizResult.next_action === 'PROCEED' ? '🚀 Recommended Next Action: Proceed to Next Subtopic' :
                           quizResult.next_action === 'REVISE' ? '🔄 Recommended Next Action: Revise Current Subtopic' :
                           '⬅️ Recommended Next Action: Revisit Prerequisite Subtopic'}
                        </strong>
                        {quizResult.next_action_reason && (
                          <div style={{ marginTop: 4, fontSize: 12, opacity: 0.95 }}>
                            {quizResult.next_action_reason}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Remediation Efficacy Tracking */}
                    {quizResult.remediation_efficacy && (
                      <div
                        style={{
                          background: '#f8fafc',
                          border: '1px solid #e2e8f0',
                          borderRadius: 8,
                          padding: '10px 14px',
                          marginBottom: 12,
                          fontSize: 12,
                        }}
                      >
                        <strong style={{ color: '#0f172a' }}>📈 Cognitive Remediation Progress:</strong>
                        <div style={{ marginTop: 4, color: '#334155' }}>
                          Status: <strong>{quizResult.remediation_efficacy.status || 'evaluated'}</strong>
                          {quizResult.remediation_efficacy.progress_percentage !== undefined && (
                            <span style={{ marginLeft: 8 }}>({quizResult.remediation_efficacy.progress_percentage}% concept improvement)</span>
                          )}
                        </div>
                        {quizResult.remediation_efficacy.resolved_areas?.length > 0 && (
                          <div style={{ marginTop: 6, display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
                            <span style={{ color: '#166534', fontWeight: 600 }}>Resolved Weaknesses:</span>
                            {quizResult.remediation_efficacy.resolved_areas.map((resArea: string, rIdx: number) => (
                              <span key={rIdx} className="badge" style={{ background: '#dcfce7', color: '#166534' }}>
                                ✓ {resArea}
                              </span>
                            ))}
                          </div>
                        )}
                        {quizResult.remediation_efficacy.remaining_weak_areas?.length > 0 && (
                          <div style={{ marginTop: 6, display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
                            <span style={{ color: '#991b1b', fontWeight: 600 }}>Remaining Challenges:</span>
                            {quizResult.remediation_efficacy.remaining_weak_areas.map((remArea: string, remIdx: number) => (
                              <span key={remIdx} className="badge" style={{ background: '#fee2e2', color: '#991b1b' }}>
                                ⚠ {remArea}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Question by question feedback */}
                    {quizResult.question_feedback?.length > 0 && (
                      <div className="q-feedback-list">
                        <strong style={{ fontSize: 13, color: '#1e293b' }}>Detailed Question-by-Question Evaluation:</strong>
                        {quizResult.question_feedback.map((qf: any) => {
                          const isCorr = qf.is_correct;
                          const isDesc = qf.question_type === 'descriptive';
                          return (
                            <div key={qf.question_id} className={`q-feedback-item ${isCorr ? 'correct' : 'incorrect'}`}>
                              <div className="q-feedback-header">
                                <strong>
                                  {isCorr ? '✅' : '❌'} Q{qf.question_id}: {qf.question_text}
                                </strong>
                                <span className="badge" style={{ background: isCorr ? '#dcfce7' : '#fee2e2', color: isCorr ? '#166534' : '#991b1b' }}>
                                  {isCorr ? 'Correct' : 'Needs Review'}
                                </span>
                              </div>

                              {isDesc ? (
                                <div>
                                  <div className="q-feedback-ans user-bad">
                                    <strong>Your Explanation:</strong> {qf.user_answer}
                                  </div>
                                  <div className="q-feedback-ans correct-ans">
                                    <strong>Ideal Principles:</strong> {qf.ideal_answer}
                                  </div>
                                  {qf.rubric_keywords?.length > 0 && (
                                    <div style={{ fontSize: 11, color: '#475569', marginTop: 4 }}>
                                      <span>Matched keywords: {qf.matched_keywords?.join(', ') || 'none'}</span>
                                      {qf.missing_keywords?.length > 0 && (
                                        <span style={{ color: '#b91c1c', marginLeft: 8 }}>Missing concepts: {qf.missing_keywords.join(', ')}</span>
                                      )}
                                    </div>
                                  )}
                                </div>
                              ) : (
                                <div>
                                  <div className={`q-feedback-ans ${isCorr ? 'correct-ans' : 'user-bad'}`}>
                                    <strong>Your Selection:</strong> {qf.user_choice_text || '(None)'}
                                  </div>
                                  {!isCorr && (
                                    <div className="q-feedback-ans correct-ans">
                                      <strong>Correct Answer:</strong> {qf.correct_choice_text}
                                    </div>
                                  )}
                                </div>
                              )}

                              {qf.explanation && (
                                <div className="q-explanation">
                                  💡 <em>{qf.explanation}</em>
                                </div>
                              )}

                              {qf.misconception && (
                                <div className="q-misc-box">
                                  ⚠️ <strong>Misconception Detected:</strong> {qf.misconception}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {quizResult.weak_areas?.length > 0 && (
                      <div style={{ marginTop: 10 }}>
                        <strong style={{ color: '#991b1b' }}>🔍 Diagnosed Weak Conceptual Areas:</strong>
                        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 4 }}>
                          {quizResult.weak_areas.map((wa: string, waIdx: number) => (
                            <span key={waIdx} className="badge" style={{ background: '#fee2e2', color: '#991b1b' }}>{wa}</span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Targeted Online Remedial Resources */}
                    {quizResult.targeted_resources?.length > 0 && (
                      <div className="remedial-box">
                        <h4>🎯 Targeted Online Resources Covering Your Weak Areas</h4>
                        <p className="muted" style={{ fontSize: 12, margin: '2px 0 10px' }}>
                          The agent automatically crawled and verified these tutorials specifically to remedy the misconceptions identified in your quiz:
                        </p>
                        {quizResult.targeted_resources.map((rem: any, rIdx: number) => (
                          <div key={rIdx} className="remedial-card">
                            <div className="remedial-card-header">
                              <div>
                                <strong>🎯 {rIdx + 1}. {rem.title}</strong>
                                <div style={{ display: 'flex', gap: 6, marginTop: 4, flexWrap: 'wrap' }}>
                                  <span className="badge badge-concept">{rem.target_concept}</span>
                                  <span className="badge badge-format">{rem.format}</span>
                                  <span className="badge badge-diff">{rem.difficulty}</span>
                                  {rem.estimated_minutes && <span className="badge" style={{ background: '#e0e7ff', color: '#4338ca' }}>⏱️ {rem.estimated_minutes} min</span>}
                                  {rem.domain && <span className="badge" style={{ background: '#f1f5f9', color: '#475569' }}>🌐 {rem.domain}</span>}
                                </div>
                              </div>
                              {rem.relevance_score && (
                                <span className="badge badge-time">Relevance: {Math.round(rem.relevance_score * 100)}%</span>
                              )}
                            </div>
                            {rem.snippet && <p style={{ fontSize: 12, color: '#475569', margin: '6px 0' }}>{rem.snippet}</p>}
                            <a href={rem.url} target="_blank" rel="noreferrer" className="remedial-btn">
                              Study Remedial Resource #{rIdx + 1} <ArrowUpRight size={13} />
                            </a>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Retake Adaptive Quiz CTA */}
                    <div style={{ marginTop: 14, paddingTop: 12, borderTop: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                      <span style={{ fontSize: 12, color: '#64748b' }}>
                        Ready to test if you've resolved misconceptions?
                      </span>
                      <button
                        type="button"
                        className="btn-quiz"
                        style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '7px 14px', fontSize: 13 }}
                        onClick={() => startQuiz(activeQuizStep, true)}
                      >
                        🔄 Retake Adaptive Quiz (Attempt #{(quizResult.attempt_number || 1) + 1})
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function ResearchJobMonitor({ jobId, initialTopic }: { jobId: string; initialTopic?: string }) {
  const [phase, setPhase] = useState<string>('starting');
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<any | null>(null);

  useEffect(() => {
    let cancelled = false;
    let timer: any = null;

    async function poll() {
      try {
        const s = await api(`/api/research/jobs/${jobId}`);
        if (cancelled) return;
        setPhase(s.phase || 'running');
        if (s.error) setError(s.error);

        if (s.phase === 'completed') {
          try {
            const rep = await api(`/api/research/jobs/${jobId}/files/latest_report.json`);
            if (!cancelled) setReport(rep);
          } catch (loadErr: any) {
            console.error('Failed to load completed report:', loadErr);
          }
          return;
        }

        if (s.phase === 'failed') {
          setError(s.error || 'The research pipeline encountered an error.');
          return;
        }

        timer = setTimeout(poll, 2500);
      } catch (err: any) {
        if (!cancelled) {
          setError(err.message || 'Error communicating with research worker.');
          timer = setTimeout(poll, 3000);
        }
      }
    }

    poll();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [jobId]);

  if (report) {
    return <ResearchReportDetailView report={report} jobId={jobId} />;
  }

  const phaseLabels: Record<string, string> = {
    starting: 'Preparing your research review…',
    planning_and_searching: 'Finding relevant academic papers…',
    downloading_and_analyzing_papers: 'Reading papers and collecting findings…',
    synthesizing_results: 'Comparing results and identifying research gaps…',
    generating_word: 'Preparing your downloadable report…',
  };

  return (
    <div className="result-panel" style={{ background: '#f8fafc', borderRadius: '14px', padding: '24px', border: '1px solid #e2e8f0', marginTop: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        {!error && <LoaderCircle className="spin" size={26} style={{ color: '#059669' }} />}
        <div>
          <h3 style={{ margin: '0 0 4px', fontSize: '18px', color: '#0f172a' }}>
            {error ? 'Literature Review Failed' : 'Preparing your research report'}
          </h3>
          <p style={{ margin: 0, fontSize: '13px', color: error ? '#b91c1c' : '#475467' }}>
            {error || (phaseLabels[phase] || `Working: ${phase.replace(/_/g, ' ')}...`)}
          </p>
        </div>
      </div>
      {initialTopic && <p style={{ fontSize: '12px', color: '#64748b', marginTop: '12px', marginBottom: 0 }}>Topic: <strong>{initialTopic}</strong></p>}
      {!error && (
        <div style={{ marginTop: '16px', background: '#e2e8f0', borderRadius: '8px', height: '6px', overflow: 'hidden' }}>
          <div style={{ background: 'linear-gradient(90deg, #10b981, #059669)', width: phase === 'starting' ? '20%' : phase === 'planning_and_searching' ? '45%' : phase === 'downloading_and_analyzing_papers' ? '70%' : '90%', height: '100%', transition: 'width 0.4s' }} />
        </div>
      )}
    </div>
  );
}

function ResearchReportDetailView({ report, jobId }: { report: any; jobId?: string }) {
  useEffect(()=>{window.dispatchEvent(new CustomEvent('phss:research-context',{detail:JSON.stringify(report).slice(0,18000)}));},[report]);
  const [exportingWord, setExportingWord] = useState(false);
  const [downloadError,setDownloadError] = useState('');
  const [gapsViewMode, setGapsViewMode] = useState<'table' | 'cards'>('table');
  const [matrixViewMode, setMatrixViewMode] = useState<'table' | 'cards'>('table');

  const agentic = report?.agentic_controller || {};
  const retrieval = agentic.retrieval_evaluation || {};
  const extraction = agentic.extraction_quality || {};
  const gaps = report?.gaps || [];
  const papers = report?.papers || [];
  const analyses = report?.paper_analyses || [];
  const clusters = report?.semantic_evidence_clusters || report?.evidence_clusters || [];

  const handleDownloadJson = () => {
    if (!report) return;
    const jsonStr = JSON.stringify(report, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${(report?.topic || 'research_report').replace(/[^a-zA-Z0-9_-]/g, '_')}_report.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleDownloadWord = async () => {
    if (!report) return;
    setExportingWord(true);setDownloadError('');
    try {
      const blob=await requestWord(report);
      saveDownload(blob,`${(report.topic || 'research_report').replace(/[^a-zA-Z0-9_-]/g,'_')}.docx`);
    } catch(err:any) {setDownloadError(err.message || 'The report could not be downloaded. Please retry.');}
    finally {setExportingWord(false);}
  };

  return (
    <div className="result-panel" style={{ marginTop: '24px' }}>
      <div className="result-head" style={{ flexWrap: 'wrap', gap: '12px', alignItems: 'flex-start' }}>
        <div>
          <span className="eyebrow" style={{ color: '#059669' }}>RESEARCH REPORT</span>
          <h3 style={{ fontSize: '22px', margin: '4px 0 6px' }}>{report?.topic || 'Literature Review'}</h3>
          <p className="muted" style={{ margin: 0, fontSize: '13px' }}>
            {papers.length} papers in this review · comparisons, findings and research gaps
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <button
            type="button"
            onClick={handleDownloadWord}
            disabled={exportingWord}
            className="primary"
            style={{ textDecoration: 'none', padding: '10px 16px', fontSize: '13px', display: 'inline-flex', alignItems: 'center', gap: '7px', cursor: 'pointer', border: 'none', borderRadius: '8px' }}
          >
            {exportingWord ? '⏳ Generating Word Doc...' : '📄 Download Word Report (.docx)'}
          </button>
          <button
            type="button"
            onClick={handleDownloadJson}
            className="secondary"
            style={{ textDecoration: 'none', padding: '10px 16px', fontSize: '13px', display: 'inline-flex', alignItems: 'center', gap: '7px', cursor: 'pointer', border: '1px solid #cbd5e1', borderRadius: '8px', background: '#f8fafc' }}
          >
            📊 Structured JSON
          </button>
        </div>
      </div>

      {downloadError&&<p className="message error" role="alert">{downloadError}</p>}
      {agentic.enabled && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px', margin: '20px 0', background: '#f8fafc', padding: '16px', borderRadius: '12px', border: '1px solid #e2e8f0' }}>
          <div>
            <div style={{ fontSize: '11px', color: '#64748b', fontWeight: 700, textTransform: 'uppercase' }}>Papers Evaluated</div>
            <div style={{ fontSize: '18px', fontWeight: 800, color: '#0f172a' }}>{retrieval.paper_count ?? papers.length} / {retrieval.requested_papers ?? papers.length}</div>
          </div>
          <div>
            <div style={{ fontSize: '11px', color: '#64748b', fontWeight: 700, textTransform: 'uppercase' }}>Topic Coverage</div>
            <div style={{ fontSize: '18px', fontWeight: 800, color: '#059669' }}>
              {typeof retrieval.topic_token_coverage === 'number' ? `${Math.round(retrieval.topic_token_coverage * 100)}%` : 'Verified'}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '11px', color: '#64748b', fontWeight: 700, textTransform: 'uppercase' }}>Field Completeness</div>
            <div style={{ fontSize: '18px', fontWeight: 800, color: '#2563eb' }}>
              {typeof extraction.completeness_ratio === 'number' ? `${Math.round(extraction.completeness_ratio * 100)}%` : 'Structured'}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '11px', color: '#64748b', fontWeight: 700, textTransform: 'uppercase' }}>Controller Decision</div>
            <div style={{ fontSize: '14px', fontWeight: 800, color: '#0f172a', textTransform: 'capitalize' }}>
              {agentic.decision ? agentic.decision.replace(/_/g, ' ') : 'Proceed'}
            </div>
          </div>
        </div>
      )}

      {/* Semantic Evidence Clusters & Research Gaps Section */}
      {(clusters.length > 0 || gaps.length > 0) && (
        <div className="research-section">
          <div className="research-section-header">
            <div>
              <h4 className="research-section-title">
                <span>💡</span> Cluster Research Gaps & Grounded Evidence
              </h4>
              <p style={{ margin: '4px 0 0', fontSize: '12px', color: '#64748b' }}>
                Recurring limitation themes clustered from extracted paper text via BGE semantic embeddings
              </p>
            </div>
            <div className="view-toggle">
              <button
                type="button"
                className={`view-toggle-btn ${gapsViewMode === 'table' ? 'active' : ''}`}
                onClick={() => setGapsViewMode('table')}
              >
                <Table size={13} /> Table View
              </button>
              <button
                type="button"
                className={`view-toggle-btn ${gapsViewMode === 'cards' ? 'active' : ''}`}
                onClick={() => setGapsViewMode('cards')}
              >
                <LayoutGrid size={13} /> Cards
              </button>
            </div>
          </div>

          {gapsViewMode === 'table' ? (
            <div className="research-table-card">
              <div className="research-table-wrapper">
                <table className="research-table">
                  <thead>
                    <tr>
                      <th style={{ width: '160px' }}>Cluster & Priority</th>
                      <th style={{ width: '270px' }}>Synthesized Research Gap</th>
                      <th style={{ minWidth: '340px' }}>Extracted Limitation Evidence Quotes</th>
                      <th style={{ width: '270px' }}>Proposed Question & Experiment</th>
                    </tr>
                  </thead>
                  <tbody>
                    {clusters.length > 0 ? (
                      clusters.map((cluster: any, idx: number) => {
                        const matchedGap = gaps[idx] || gaps[0];
                        const prio = typeof cluster.cluster_priority === 'number' ? cluster.cluster_priority : 0.65;
                        const prioClass = prio >= 0.65 ? 'priority-high' : prio >= 0.55 ? 'priority-mid' : 'priority-low';
                        const evidenceList = cluster.evidence || [];
                        return (
                          <tr key={cluster.cluster_id ?? idx}>
                            <td>
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                                <div className="cluster-badge">
                                  <span>Cluster #{cluster.cluster_id ?? idx}</span>
                                </div>
                                <div>
                                  <span className={`priority-pill ${prioClass}`}>
                                    Priority: {typeof prio === 'number' ? prio.toFixed(2) : prio}
                                  </span>
                                </div>
                                <div style={{ fontSize: '11px', color: '#64748b' }}>
                                  <strong>{cluster.unique_paper_count || 1}</strong> paper(s) cited
                                </div>
                                <div style={{ fontSize: '11px', color: '#64748b' }}>
                                  <strong>{cluster.evidence_count || evidenceList.length}</strong> quote(s)
                                </div>
                                {typeof cluster.average_relevance === 'number' && (
                                  <div style={{ fontSize: '11px', color: '#059669', fontWeight: 600 }}>
                                    Avg Rel: {(cluster.average_relevance * 100).toFixed(0)}%
                                  </div>
                                )}
                              </div>
                            </td>
                            <td>
                              {matchedGap ? (
                                <div>
                                  <div style={{ fontWeight: 800, fontSize: '13.5px', color: '#064e3b', marginBottom: '6px' }}>
                                    {matchedGap.title}
                                  </div>
                                  <div style={{ fontSize: '12px', color: '#334155', lineHeight: 1.45 }}>
                                    <strong>Underlying Constraint:</strong> {matchedGap.rationale}
                                  </div>
                                </div>
                              ) : (
                                <div style={{ fontSize: '12px', color: '#64748b', fontStyle: 'italic' }}>
                                  Evidence cluster synthesized from {cluster.unique_paper_count || 1} paper(s).
                                </div>
                              )}
                            </td>
                            <td>
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                {evidenceList.slice(0, 4).map((ev: any, evIdx: number) => (
                                  <div key={evIdx} className="evidence-quote-item">
                                    <p className="evidence-quote-text">
                                      "{ev.sentence || ev.text}"
                                    </p>
                                    <div className="evidence-source-row">
                                      <a
                                        href={ev.paper_url || '#'}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="evidence-source-link"
                                        title={ev.paper_title}
                                      >
                                        📄 {ev.paper_title || `Paper ${ev.paper_index ?? (evIdx + 1)}`} <ArrowUpRight size={11} />
                                      </a>
                                      {typeof ev.relevance === 'number' && (
                                        <span className="relevance-score-badge">
                                          {(ev.relevance * 100).toFixed(0)}% match
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </td>
                            <td>
                              {matchedGap ? (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                  {matchedGap.research_question && (
                                    <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '8px', padding: '9px 11px', fontSize: '12px', color: '#166534' }}>
                                      <strong style={{ display: 'block', color: '#14532d', marginBottom: '3px', fontSize: '11px', textTransform: 'uppercase' }}>
                                        Research Question
                                      </strong>
                                      {matchedGap.research_question}
                                    </div>
                                  )}
                                  {matchedGap.proposed_experiment && (
                                    <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '9px 11px', fontSize: '12px', color: '#334155' }}>
                                      <strong style={{ display: 'block', color: '#475569', marginBottom: '3px', fontSize: '11px', textTransform: 'uppercase' }}>
                                        Proposed Experiment
                                      </strong>
                                      {matchedGap.proposed_experiment}
                                    </div>
                                  )}
                                </div>
                              ) : (
                                <div style={{ fontSize: '12px', color: '#64748b' }}>
                                  Empirically evaluate cross-paper constraints against baseline models.
                                </div>
                              )}
                            </td>
                          </tr>
                        );
                      })
                    ) : (
                      gaps.map((g: any, i: number) => (
                        <tr key={i}>
                          <td>
                            <div className="cluster-badge">
                              <span>Gap #{i + 1}</span>
                            </div>
                            <div style={{ marginTop: '6px' }}>
                              <span className="priority-pill priority-high">High Priority</span>
                            </div>
                          </td>
                          <td>
                            <div style={{ fontWeight: 800, fontSize: '13.5px', color: '#064e3b', marginBottom: '6px' }}>
                              {g.title}
                            </div>
                            <div style={{ fontSize: '12px', color: '#334155', lineHeight: 1.45 }}>
                              <strong>Underlying Issue:</strong> {g.rationale}
                            </div>
                          </td>
                          <td>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                              {(g.evidence_ids || []).map((ev: string, evIdx: number) => (
                                <div key={evIdx} className="evidence-quote-item">
                                  <p className="evidence-quote-text">
                                    "{ev}"
                                  </p>
                                </div>
                              ))}
                            </div>
                          </td>
                          <td>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                              {g.research_question && (
                                <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '8px', padding: '9px 11px', fontSize: '12px', color: '#166534' }}>
                                  <strong style={{ display: 'block', color: '#14532d', marginBottom: '3px', fontSize: '11px', textTransform: 'uppercase' }}>
                                    Research Question
                                  </strong>
                                  {g.research_question}
                                </div>
                              )}
                              {g.proposed_experiment && (
                                <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '9px 11px', fontSize: '12px', color: '#334155' }}>
                                  <strong style={{ display: 'block', color: '#475569', marginBottom: '3px', fontSize: '11px', textTransform: 'uppercase' }}>
                                    Proposed Experiment
                                  </strong>
                                  {g.proposed_experiment}
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div style={{ display: 'grid', gap: '14px' }}>
              {gaps.map((g: any, i: number) => (
                <div key={i} style={{ background: '#fff', border: '1px solid #e2e8f0', borderLeft: '4px solid #10b981', borderRadius: '10px', padding: '16px 20px', boxShadow: '0 2px 8px rgba(0,0,0,0.03)' }}>
                  <h5 style={{ margin: '0 0 8px', fontSize: '15px', color: '#064e3b', fontWeight: 700 }}>{g.title}</h5>
                  <p style={{ margin: '0 0 8px', fontSize: '13px', color: '#334155', lineHeight: 1.5 }}>
                    <strong>Underlying Issue:</strong> {g.rationale}
                  </p>
                  {g.research_question && (
                    <p style={{ margin: '0 0 8px', fontSize: '13px', color: '#1e293b' }}>
                      <strong>Research Question:</strong> {g.research_question}
                    </p>
                  )}
                  {g.proposed_experiment && (
                    <p style={{ margin: '0 0 8px', fontSize: '13px', color: '#475467' }}>
                      <strong>Proposed Experiment:</strong> {g.proposed_experiment}
                    </p>
                  )}
                  {g.evidence_ids && g.evidence_ids.length > 0 && (
                    <div style={{ marginTop: '8px', fontSize: '11px', color: '#64748b' }}>
                      <strong>Cited Evidence:</strong> {g.evidence_ids.join(' · ')}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Extracted Methodology & Paper Analysis (Literature Review Comparison Matrix) */}
      {analyses.length > 0 && (
        <div className="research-section">
          <div className="research-section-header">
            <div>
              <h4 className="research-section-title">
                <span>📑</span> Literature Review Comparison Matrix (6-Column Extraction)
              </h4>
              <p style={{ margin: '4px 0 0', fontSize: '12px', color: '#64748b' }}>
                Comparative matrix across methodology, datasets, empirical metrics, limitations, and candidate gaps
              </p>
            </div>
            <div className="view-toggle">
              <button
                type="button"
                className={`view-toggle-btn ${matrixViewMode === 'table' ? 'active' : ''}`}
                onClick={() => setMatrixViewMode('table')}
              >
                <Table size={13} /> Table View
              </button>
              <button
                type="button"
                className={`view-toggle-btn ${matrixViewMode === 'cards' ? 'active' : ''}`}
                onClick={() => setMatrixViewMode('cards')}
              >
                <LayoutGrid size={13} /> Cards
              </button>
            </div>
          </div>

          {matrixViewMode === 'table' ? (
            <div className="research-table-card">
              <div className="research-table-wrapper">
                <table className="research-table matrix-table">
                  <thead>
                    <tr>
                      <th style={{ width: '190px' }}>Paper & Year</th>
                      <th style={{ width: '220px' }}>Methodology</th>
                      <th style={{ width: '180px' }}>Datasets / Benchmarks</th>
                      <th style={{ width: '200px' }}>Key Results & Metrics</th>
                      <th style={{ width: '200px' }}>Author Limitations</th>
                      <th style={{ width: '200px' }}>Potential Gap from Evidence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analyses.map((pa: any, i: number) => (
                      <tr key={i}>
                        <td>
                          <div style={{ fontWeight: 700, fontSize: '13px', color: '#0f172a', marginBottom: '4px' }}>
                            {pa.url ? (
                              <a href={pa.url} target="_blank" rel="noreferrer" style={{ color: '#0f172a', textDecoration: 'none' }} className="evidence-source-link">
                                {pa.title || `Paper ${i + 1}`} <ArrowUpRight size={12} />
                              </a>
                            ) : (
                              pa.title || `Paper ${i + 1}`
                            )}
                          </div>
                          <div style={{ fontSize: '11px', color: '#64748b' }}>
                            {pa.year ? `Year: ${pa.year}` : ''} {pa.authors?.length ? `· ${Array.isArray(pa.authors) ? pa.authors.slice(0, 2).join(', ') : pa.authors}` : ''}
                          </div>
                          <div style={{ marginTop: '6px' }}>
                            <span className="cluster-badge" style={{ fontSize: '10px', padding: '2px 6px' }}>
                              Paper [{pa.paper_index ?? (i + 1)}]
                            </span>
                          </div>
                        </td>
                        <td>
                          <div className="matrix-cell-content">
                            {pa.methodology || 'Not reported in extracted text'}
                          </div>
                        </td>
                        <td>
                          <div className="matrix-cell-content">
                            {pa.dataset || pa.datasets || 'Benchmark datasets referenced in paper.'}
                          </div>
                        </td>
                        <td>
                          <div className="matrix-cell-content">
                            {pa.results_metrics || pa.results || 'Refer to publication text for detailed metrics.'}
                          </div>
                        </td>
                        <td>
                          <div className="matrix-cell-content" style={{ color: '#991b1b', background: '#fef2f2', padding: '8px 10px', borderRadius: '6px', border: '1px solid #fee2e2' }}>
                            {pa.author_stated_limitations || pa.limitations || 'None explicitly stated in extracted section.'}
                          </div>
                        </td>
                        <td>
                          <div className="matrix-cell-content" style={{ color: '#065f46', background: '#ecfdf5', padding: '8px 10px', borderRadius: '6px', border: '1px solid #d1fae5' }}>
                            {pa.potential_gap_from_evidence || pa.potential_gap_from_abstract || 'Extracted limitation provides candidate research direction.'}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div style={{ display: 'grid', gap: '14px' }}>
              {analyses.map((pa: any, i: number) => (
                <div key={i} style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: '12px', padding: '18px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'wrap', gap: '8px' }}>
                    <strong style={{ fontSize: '14px', color: '#0f172a' }}>{pa.title || `Paper ${i + 1}`}</strong>
                    <span style={{ fontSize: '11px', color: '#64748b' }}>{pa.year || 'n.d.'}</span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '10px', marginTop: '12px', fontSize: '12px' }}>
                    <div style={{ background: '#f8fafc', padding: '10px', borderRadius: '8px' }}>
                      <div style={{ fontWeight: 700, color: '#334155' }}>Methodology</div>
                      <div style={{ color: '#64748b', marginTop: '4px' }}>{pa.methodology || 'Not reported'}</div>
                    </div>
                    <div style={{ background: '#f8fafc', padding: '10px', borderRadius: '8px' }}>
                      <div style={{ fontWeight: 700, color: '#334155' }}>Datasets / Benchmarks</div>
                      <div style={{ color: '#64748b', marginTop: '4px' }}>{pa.dataset || pa.datasets || 'Not reported'}</div>
                    </div>
                    <div style={{ background: '#f8fafc', padding: '10px', borderRadius: '8px' }}>
                      <div style={{ fontWeight: 700, color: '#334155' }}>Key Results & Metrics</div>
                      <div style={{ color: '#64748b', marginTop: '4px' }}>{pa.results_metrics || pa.results || 'Not reported'}</div>
                    </div>
                    <div style={{ background: '#fef2f2', padding: '10px', borderRadius: '8px' }}>
                      <div style={{ fontWeight: 700, color: '#991b1b' }}>Stated Limitations</div>
                      <div style={{ color: '#7f1d1d', marginTop: '4px' }}>{pa.author_stated_limitations || pa.limitations || 'None reported'}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {papers.length > 0 && analyses.length === 0 && (
        <div className="paper-list" style={{ marginTop: '20px' }}>
          {papers.map((p: any, i: number) => (
            <article className="paper" key={p.url || i}>
              <div className="paper-index">{String(i + 1).padStart(2, '0')}</div>
              <div>
                <a href={p.url || p.pdf_url} target="_blank" rel="noreferrer">
                  {p.title || 'Untitled paper'} <ArrowUpRight size={13} />
                </a>
                <p>{p.summary || p.abstract}</p>
                <small>
                  {p.authors?.join(', ')} {p.published ? ` · ${p.published.slice(0, 10)}` : ''} {p.source ? ` · [${p.source}]` : ''}
                </small>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

function ResultView({ result, onSwitchWorkspace, onHandoff }: { result: any; onSwitchWorkspace?: () => void; onHandoff?: (agent:string,message:string,topic:string)=>void }) {
  const [showRaw, setShowRaw] = useState(false);

  if (result?.agent_results) {
    return <RoutedResult result={result} renderChild={r=><ResultView result={r} onHandoff={onHandoff}/>} onHandoff={onHandoff || (()=>{})}/>;
  }
  if (result?.researchJob) {
    return <ResearchJobMonitor jobId={result.researchJob} initialTopic={result.topic} />;
  }

  if (result?.research?.papers || result?.papers || result?.paper_analyses || result?.research_gap_synthesis) {
    const data = result.research || result;
    return <ResearchReportDetailView report={data} jobId={data.jobId} />;
  }

  if (result?.plan || result?.steps) {
    const plan = result.plan || result;
    return <LearningPlanView plan={plan} onSwitchWorkspace={onSwitchWorkspace} />;
  }

  return (
    <div className="result-panel">
      <div className="result-head">
        <h3>PHSS response</h3>
        <button className="text-button" onClick={() => setShowRaw(v => !v)}>
          {showRaw ? 'Hide details' : 'Show details'}
        </button>
      </div>
      <p>{result.message || result.feedback?.message || 'Request completed.'}</p>
      {result.workspace && <a href={result.workspace}>Open workspace <ArrowUpRight size={14} /></a>}
      {showRaw && <pre>{JSON.stringify(result, null, 2)}</pre>}
    </div>
  );
}



