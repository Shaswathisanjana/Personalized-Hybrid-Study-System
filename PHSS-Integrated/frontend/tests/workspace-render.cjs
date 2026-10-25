// Render the real application with signed-in fixtures; no browser or network.
const {build}=require('esbuild');
const {readFileSync}=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const Module=require('node:module');
const root=path.resolve(__dirname,'..');
async function render(tab,mode,result){
 const output=await build({stdin:{contents:"import App from './src/App'; import {renderToStaticMarkup} from 'react-dom/server'; export default renderToStaticMarkup(<App/>);",resolveDir:root,loader:'tsx'},bundle:true,jsx:'automatic',platform:'node',format:'cjs',write:false,
 plugins:[{name:'fixtures',setup(b){b.onLoad({filter:/\/src\/App.tsx$/},args=>{
 let source=readFileSync(args.path,'utf8')
 .replace("useState<User | null>(null)","useState<User | null>({userId:'test',name:'Student',email:'test@example.com'})")
 .replace("useState<Tab>('assistant')","useState<Tab>('"+tab+"')")
 .replace("useState<'review'|'practice'>('review')","useState<'review'|'practice'>('"+mode+"')")
 .replace("const [journeys, setJourneys] = useState<any[]>([])","const [journeys, setJourneys] = useState<any[]>([{id:'python',topic_title:'Python',plan:{steps:[{order:1,concept:'Variables'},{order:2,concept:'Loops'}],quizProgress:{total:2,attempted:1,completed:0,percentage:0,lessons:{'1:Variables':{attempted:true,passed:false,score:0.5}}}}}])")
 .replace("const [result, setResult] = useState<any>(null)","const [result, setResult] = useState<any>("+JSON.stringify(result)+")");
 return {contents:source,loader:'tsx',resolveDir:path.dirname(args.path)};
 });}}]});
 const mod=new Module(path.join(root,'fixture.cjs'),module);mod.paths=module.paths;mod.filename=path.join(root,"fixture.cjs");
 mod._compile(output.outputFiles[0].text,mod.filename);
 return mod.exports.default;
}
(async()=>{
 const review={agent:'orchestrator',agent_results:[{agent:'coding',success:true,review:{summary:'Review result',learning_concept:'Indexing',issues:[],corrected_code:'print(1)'}}],handoffs:[]};
 const code=await render('coding','review',review);
 assert.ok(code.includes('Review result'));
 assert.ok(!code.includes('<iframe'));
 assert.ok(!code.includes('WELCOME BACK'));
 assert.ok(!code.includes('class="agent-grid"'));
 const practice=await render('coding','practice',null);
 assert.ok(practice.includes('<iframe'));
 const lesson=await render('learning','review',{plan:{topic:'DSA trees',steps:[],quizProgress:{lessons:{}}}});
 assert.ok(!lesson.includes('Generate learning path'));
 assert.ok(!lesson.includes('WELCOME BACK'));
 const home=await render('assistant','review',null);
 assert.ok(home.includes('My courses'));
 assert.ok(home.includes('Quizzes completed'));
 assert.ok(home.includes('1/2 module quizzes completed'));
 assert.ok(home.includes('50% · Needs revision'));
 assert.ok(home.includes('Not taken'));

 assert.ok(!home.includes('Explore learning topics'));
 const quizPage=await render('learning','review',{plan:{topic:'Trees',currentLevel:'advanced',steps:[{order:1,concept:'Traversals',title:'Tree guide',url:'https://example.com/trees'}],quizProgress:{lessons:{'1:Traversals':{attempted:true,passed:true}}}}});
 assert.match(quizPage,/<button[^>]*class="quiz-action"[^>]*>Retake lesson quiz/);
 const quizButton=quizPage.match(/<button[^>]*class="quiz-action"[^>]*>/)[0];
 assert.ok(!quizButton.includes('disabled'));
 assert.ok(quizPage.includes('Learning level (optional)'));
 assert.ok(!home.includes('class="agent-grid"'));
 const research=await render('research','review',{research:{review_mode:'evolution',topic:'LDA',papers:[{source_id:'S1',title:'Survey',url:'https://example.com'}],coverage:{analyzed:1,survey_papers:1,full_text_available:1},research_progression:{timeline:[{title:'A research milestone',description:'Evidence-backed progression',source_ids:['S1']}],learning_concepts:['Topic modeling']}}});
 assert.ok(research.includes('A research milestone'));
 assert.ok(research.includes('Learn Topic modeling'));
 assert.ok(!research.includes('Number of papers to analyze'));
 assert.ok(!research.includes('Paper-wise comparison'));
 console.log('Workspace rendering: code review, interview, direct roadmap and enrolled course home passed.');
})().catch(e=>{console.error(e);process.exitCode=1;});
