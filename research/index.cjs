'use strict';
const path=require('node:path'), fs=require('node:fs/promises'), crypto=require('node:crypto');
const {spawn}=require('node:child_process');
const express=require('express');
const ROOT=path.resolve(__dirname,'../outputs');
const USER=/^[a-zA-Z0-9_-]{1,80}$/, JOB=/^[0-9a-f-]{36}$/;
const FILES=new Set(['latest_report.json','extracted_paper_sections.json','research_report.docx']);
function installResearch({app, outputRoot=ROOT, spawnWorker=spawn}) {
  const active=new Map();
  const router=express.Router();
  router.use((req,res,next)=>{
    res.set('Cache-Control','no-store');
    const origin=req.get('origin');
    if(origin) { try {if(new URL(origin).host!==req.get('host')) return res.status(403).json({error:'Use this API from the learning app.'});} catch {return res.status(403).json({error:'Invalid origin.'});} }
    const user=req.body?.userId || req.query.userId;
    if(typeof user!=='string' || !USER.test(user)) return res.status(400).json({error:'Use a Student ID with 1–80 letters, digits, underscores or hyphens.'});
    req.researchUser=user;next();
  });
  const route=fn=>(req,res,next)=>Promise.resolve(fn(req,res)).catch(next);
  function folder(req) {
    if(!JOB.test(req.params.jobId)) {const e=new Error('Invalid research job ID.');e.status=400;throw e;}
    return path.join(outputRoot,req.researchUser,req.params.jobId);
  }
  async function write(file,data){const tmp=file+'.node.tmp';await fs.writeFile(tmp,JSON.stringify(data,null,2));await fs.rename(tmp,file);}
  router.post('/jobs',route(async(req,res)=>{
    const {topic}=req.body,count=req.body.count ?? 10;
    if(typeof topic!=='string' || !topic.trim() || topic.length>300 || !Number.isInteger(count) || count<1 || count>10) return res.status(400).json({error:'Enter a topic up to 300 characters and a paper count from 1 to 10.'});
    if(!process.env.GEMINI_API_KEY)return res.status(503).json({error:'Set GEMINI_API_KEY in .env and restart the server.'});
    if(active.size)return res.status(409).json({error:'A research job is running. Wait until it finishes.'});
    const jobId=crypto.randomUUID(),dir=path.join(outputRoot,req.researchUser,jobId);
    // Reserve before any await so concurrent requests cannot launch extra workers.
    active.set(jobId,null);
    try {
      await fs.mkdir(dir,{recursive:true});
      await write(path.join(dir,'request.json'),{topic:topic.trim(),count,userId:req.researchUser,createdAt:new Date().toISOString()});
      await write(path.join(dir,'status.json'),{phase:'starting'});
      const child=spawnWorker(process.env.RESEARCH_PYTHON || 'python',[path.join(__dirname,'pipeline.py'),'--topic',topic.trim(),'--count',String(count),'--output',dir],{shell:false,stdio:['ignore','ignore','pipe'],env:process.env});
      active.set(jobId,child);let finished=false;
      const timer=setTimeout(()=>{child.kill();void finish('Research job exceeded the 60-minute limit. Try fewer papers.');},3600000);timer.unref?.();
      // Do not return provider responses or environment secrets to the browser.
      child.stderr?.on('data',()=>{});
      async function finish(error){
        if(finished)return;finished=true;clearTimeout(timer);
        try {let state;try{state=JSON.parse(await fs.readFile(path.join(dir,'status.json'),'utf8'));}catch{}
          if(error && !['completed','failed'].includes(state?.phase)) await write(path.join(dir,'status.json'),{phase:'failed',error});
        } finally {active.delete(jobId);}
      }
      child.once('error',()=>{void finish('Python worker could not start. Check RESEARCH_PYTHON and install research/requirements.txt.');});
      child.once('exit',code=>{void finish(code===0?null:'Python worker stopped. Check the Python environment and research dependencies.');});
      res.status(202).json({jobId});
    } catch(e){active.delete(jobId);throw e;}
  }));
  router.get('/jobs',route(async(req,res)=>{
    const userDir=path.join(outputRoot,req.researchUser);let names=[];
    try{names=await fs.readdir(userDir);}catch(e){if(e.code!=='ENOENT')throw e;}
    const jobs=[];
    for(const jobId of names.filter(x=>JOB.test(x))){try {const request=JSON.parse(await fs.readFile(path.join(userDir,jobId,'request.json'),'utf8'));jobs.push({jobId,...request});}catch{}}
    jobs.sort((a,b)=>b.createdAt.localeCompare(a.createdAt));res.json({jobs:jobs.slice(0,30)});
  }));
  router.get('/jobs/:jobId',route(async(req,res)=>{
    const dir=folder(req),state=JSON.parse(await fs.readFile(path.join(dir,'status.json'),'utf8'));
    if(!active.has(req.params.jobId)&&!['failed','completed'].includes(state.phase)) {state.phase='failed';state.error='Job interrupted by a server restart. Start a new review.';await write(path.join(dir,'status.json'),state);}
    res.json(state);
  }));
  router.get('/jobs/:jobId/files/:filename',route(async(req,res)=>{
    const dir=folder(req);if(!FILES.has(req.params.filename))return res.status(404).json({error:'Unknown output file.'});
    const state=JSON.parse(await fs.readFile(path.join(dir,'status.json'),'utf8'));
    if(state.phase!=='completed') return res.status(409).json({error:'Report is not ready. Wait for the job to complete.'});
    res.download(path.join(dir,req.params.filename),req.params.filename,e=>{if(e&&!res.headersSent)res.status(404).json({error:'Output file is unavailable.'});});
  }));
  router.use((e,req,res,next)=>res.status(e.status || (e.code==='ENOENT'?404:500)).json({error:e.code==='ENOENT'?'Research job not found.':'Research request failed. '+(e.status?e.message:'Check server configuration.')}));
  app.use('/api/research',router);
  app.use('/research',express.static(path.join(__dirname,'public')));
  return {active};
}
module.exports={installResearch};
