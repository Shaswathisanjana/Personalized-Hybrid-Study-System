import { BookOpen, ArrowUpRight, GraduationCap, Compass, CheckCircle2 } from 'lucide-react';
export function courseStats(courses:any[]){const completed=courses.filter(c=>c.plan?.quizProgress?.total>0&&c.plan.quizProgress.completed===c.plan.quizProgress.total).length;return {enrolled:courses.length,completed,inProgress:courses.length-completed};}
const catalog=[
 {title:'English communication',tag:'LANGUAGE & CONFIDENCE',description:'Build everyday vocabulary, grammar, and confidence in conversations.',icon:'Aa'},
 {title:'Python fundamentals',tag:'BEGINNER',description:'Build a foundation in variables, loops, functions, and problem solving.',icon:'Py'},
 {title:'Data structures and algorithms',tag:'CODING FOUNDATIONS',description:'Learn arrays, linked lists, trees, and the ideas behind efficient solutions.',icon:'{}'},
 {title:'Machine learning foundations',tag:'AI & DATA SCIENCE',description:'Explore models, training, evaluation, and practical learning concepts.',icon:'ML'},
 {title:'SQL and databases',tag:'DATA SKILLS',description:'Understand queries, relationships, joins, and organizing data.',icon:'DB'}
];
export function CourseDashboard({courses,loading,error,onResume,onExplore}:{courses:any[];loading:boolean;error:string;onResume:(course:any)=>void;onExplore:(topic:string)=>void}){
 const stats=courseStats(courses);
 return <section className="course-dashboard">
  {error?<p className="message error" role="alert">{error}</p>:loading?<p role="status">Loading your courses…</p>:<>
   <div className="result-head"><div><p className="eyebrow">KEEP YOUR MOMENTUM</p><h2>My courses</h2></div><span className="muted">Your enrolled learning roadmaps</span></div>
   {!courses.length?<div className="course-empty"><BookOpen size={30}/><h3>Your next chapter starts here</h3><p>Ask PHSS for a learning roadmap, then choose “Enroll in course” to save it here.</p></div>:<div className="course-grid">{courses.map((c:any)=>{const q=c.plan?.quizProgress,done=q?.completed||0,total=q?.total||c.total_lessons||0,percent=q?.percentage||0,attempted=q?.attempted??Object.values(q?.lessons||{}).filter((x:any)=>x.attempted).length,attemptPercent=total?Math.round(attempted*100/total):0;return <article className="course-resume-card" key={c.id||c.topic_title}><div className="course-card-top"><span className="course-symbol"><BookOpen size={22}/></span><span className="course-tag">{percent===100?'Completed':'Enrolled'}</span></div><h3>{c.topic_title}</h3><p>{c.learning_goal||'Continue your learning roadmap.'}</p><div className="course-progress-label"><span>Quizzes completed</span><strong>{attemptPercent}%</strong></div><progress value={attemptPercent} max={100}/><small>{attempted}/{total||'—'} module quizzes completed · {done}/{total||'—'} passed ({percent}%)</small><details className="course-quiz-details"><summary>Module quiz results</summary>{(c.plan?.steps||[]).map((step:any)=>{const key=String(step.order||'')+':'+String(step.concept||step.title).slice(0,140),state=q?.lessons?.[key];return <div className="course-quiz-row" key={key}><span>{step.concept||step.title}</span><strong>{!state?.attempted?'Not taken':state.score==null?(state.passed?'Passed':'Needs revision'):Math.round(state.score*100)+'% · '+(state.passed?'Passed':'Needs revision')}</strong></div>;})}</details><button className="primary" onClick={()=>onResume(c)}>{percent===100?'Review course':'Continue learning'} <ArrowUpRight size={16}/></button></article>;})}</div>}
  </>}

 </section>;
}
