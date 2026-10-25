const {buildSync}=require('esbuild');
const vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const fs=require('node:fs'),os=require('node:os'),cp=require('node:child_process');
const root=path.resolve(__dirname,'..');
const output=buildSync({entryPoints:[path.join(root,'src/reportDownload.ts')],bundle:true,write:false,platform:'node',format:'cjs'});
const box={module:{exports:{}},exports:{}};vm.runInNewContext(output.outputFiles[0].text,box);
const {exportPayload}=box.module.exports;
const report={review_mode:'evolution',topic:'Agentic systems',selection_reason:'Relevant sources',
 papers:[{source_id:'S40',title:'Selected survey',url:'https://example.com/paper',is_survey:true,pdf_path:'/private/source.pdf'}],
 paper_analyses:[{source_id:'S40',title:'Selected survey',url:'https://example.com/paper',methodology:'Evidence'}],
 coverage:{searched_at:'2026-10-25',limitations:'Bounded review'},
 research_progression:{current_state:[{title:'Current finding',description:'Supported statement',source_ids:['S40']}]},
 research_gap_synthesis:'A gap [S40]',userId:'private-user',api_key:'never-export'};
const payload=exportPayload(report);
assert.equal(payload.review_mode,'evolution');
assert.equal(payload.papers[0].source_id,'S40');
assert.equal(payload.paper_analyses[0].source_id,'S40');
assert.equal(payload.research_progression.current_state[0].source_ids[0],'S40');
assert.equal(payload.coverage.searched_at,'2026-10-25');
assert.equal(payload.papers[0].pdf_path,undefined);
assert.equal(payload.api_key,undefined);
assert.equal(payload.userId,undefined);
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'phss-export-test-'));
try{
 const fixture=path.join(temp,'report.json');fs.writeFileSync(fixture,JSON.stringify(payload));
 // Pass code as an argument, without shell interpolation.
 const pythonScript="import json,sys,io\nfrom app.agents.research.word_export import export_word_report\nfrom docx import Document\ndata=json.load(open(sys.argv[1]))\ndocument=Document(io.BytesIO(export_word_report(data)))\ntext=' '.join(p.text for p in document.paragraphs)\nassert 'Research Literature Review and Progression' in text\nassert 'Current finding' in text\nassert '[S40]' in text\nassert 'Paper-wise comparison' not in text\nprint('Browser payload -> Python export -> progression DOCX passed.')";
 cp.execFileSync(process.env.PYTHON||'python',['-c',pythonScript.replaceAll('\n',String.fromCharCode(10)),fixture],{env:{...process.env,PYTHONPATH:path.join(root,'../backend-python')},stdio:'inherit'});
}finally{fs.rmSync(temp,{recursive:true,force:true});}
