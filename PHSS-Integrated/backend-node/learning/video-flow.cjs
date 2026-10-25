'use strict';
const axios = require('axios');
const crypto = require('node:crypto');
const VIDEO_ID = /^[A-Za-z0-9_-]{11}$/;
const cache = new Map(), pending = new Map();
const words = s => [...new Set(String(s).toLowerCase().match(/[a-z0-9]+/g) || [])].filter(w => w.length>2 && !['the','and','for','with','tutorial','foundations','introduction','basics'].includes(w));
function seconds(iso='') { const m=/^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$/.exec(iso); return m ? Number(m[1]||0)*3600+Number(m[2]||0)*60+Number(m[3]||0) : 0; }
function rankVideos(videos, concept, level) {
 const tokens=words(concept);
 return videos.map(v=>{const text=(v.title+' '+v.description).toLowerCase();const matches=tokens.filter(t=>text.includes(t)).length;const relevance=tokens.length?matches/tokens.length:0;
 const levelMatch=level==='beginner'? /intro|beginner|explained|basics|fundamental/i.test(text) : level==='advanced'?/advanced|lecture|implementation|research/i.test(text):/tutorial|lecture|implementation/i.test(text);
 const score=relevance*.8+(levelMatch?.12:0)+(v.duration>=180&&v.duration<=3600?.08:0);
 return {...v,score:Math.round(score*100),reason:`Matches ${matches}/${tokens.length} topic terms${levelMatch?'; description matches your level':''}. ${Math.ceil(v.duration/60)} min. Metadata-based recommendation; confirm the lesson fits your goal.`};
 }).filter(v=>v.score>=35).sort((a,b)=>b.score-a.score).slice(0,3);
}
function mergeCoverage(existing, incoming, duration) {
 const normalized=[...existing,...incoming].filter(x=>Array.isArray(x)&&x.length===2&&x.every(Number.isFinite)).map(([a,b])=>[Math.max(0,a),Math.min(duration,b)]).filter(([a,b])=>b>a).sort((a,b)=>a[0]-b[0]);
 const merged=[];for(const pair of normalized){const last=merged.at(-1);if(last&&pair[0]<=last[1]+.1)last[1]=Math.max(last[1],pair[1]);else merged.push(pair);}
 return merged;
}
async function recommendations(concept,level,existingId='') {
 const key=process.env.YOUTUBE_API_KEY;if(!key) {const e=Error('Specific video recommendations need YOUTUBE_API_KEY in backend-node/.env. Enable YouTube Data API v3 for that key, then restart.');e.status=503;throw e;}
 const cacheKey=JSON.stringify([concept,level,existingId]);const cached=cache.get(cacheKey);if(cached&&cached.until>Date.now())return cached.videos;
 if(pending.has(cacheKey))return pending.get(cacheKey);
 const work=(async()=>{
  const r=await axios.get('https://www.googleapis.com/youtube/v3/search',{params:{key,part:'snippet',type:'video',videoEmbeddable:'true',maxResults:8,q:`${concept} ${level} tutorial`,safeSearch:'strict'},timeout:15000});
  const ids=[...new Set([existingId,...(r.data.items||[]).map(i=>i.id.videoId)].filter(x=>VIDEO_ID.test(x)))];if(!ids.length)return [];
  const detail=await axios.get('https://www.googleapis.com/youtube/v3/videos',{params:{key,part:'snippet,contentDetails,status',id:ids.join(',')},timeout:15000});
  const videos=(detail.data.items||[]).filter(i=>i.status?.embeddable&&i.status?.privacyStatus==='public'&&!i.snippet?.liveBroadcastContent?.match(/live|upcoming/)).map(i=>({videoId:i.id,title:i.snippet.title,channel:i.snippet.channelTitle,description:i.snippet.description.slice(0,1500),thumbnail:i.snippet.thumbnails?.medium?.url,duration:seconds(i.contentDetails.duration),url:`https://www.youtube.com/watch?v=${i.id}`})).filter(v=>v.duration>0);
  const ranked=rankVideos(videos,concept,level);cache.set(cacheKey,{until:Date.now()+3600000,videos:ranked});if(cache.size>300)cache.delete(cache.keys().next().value);return ranked;
 })();pending.set(cacheKey,work);try{return await work;}finally{pending.delete(cacheKey);}
}
function installVideoFlow({app,mongoose}) {
 const schema=new mongoose.Schema({userId:{type:String,required:true},topic:String,lessonKey:String,concept:String,videoId:String,title:String,url:String,duration:Number,position:Number,coverage:{type:[[Number]],default:[]},watchedSeconds:{type:Number,default:0},watchPercent:{type:Number,default:0},completed:{type:Boolean,default:false}},{timestamps:true});
 schema.index({userId:1,topic:1,lessonKey:1},{unique:true});const Progress=mongoose.models.LessonVideoProgress||mongoose.model('LessonVideoProgress',schema);
 const locks=new Map();
 async function locked(key,fn){const prior=locks.get(key)||Promise.resolve();const next=prior.catch(()=>{}).then(fn);locks.set(key,next);try{return await next;}finally{if(locks.get(key)===next)locks.delete(key);}}
 app.get('/api/learning/videos',async(req,res)=>{try{const concept=String(req.query.concept||'').trim().slice(0,250);if(!concept)return res.status(400).json({error:'A lesson concept is required.'});let level=['beginner','intermediate','advanced'].includes(req.query.level)?req.query.level:'beginner';let adaptation='Matched to your selected learning level.';if(mongoose.connection?.db){const latest=await mongoose.connection.db.collection('quiz_attempts').findOne({userId:req.authUserId,conceptName:concept},{sort:{createdAt:-1}});if(latest&&latest.passed===false){level='beginner';adaptation='Your latest quiz showed gaps in this concept; introductory explanations are prioritized.';}else if(latest?.passed){adaptation='Your latest quiz passed. Continue to the next roadmap concept, or reinforce this one.';}}res.json({videos:await recommendations(concept,level,String(req.query.videoId||'')),source:'YouTube Data API',adaptation,ranking:'Topic relevance, level cues and lesson duration'});}catch(e){res.status(e.status||502).json({error:e.status?e.message:'YouTube recommendations could not be retrieved. Check API-key permissions and quota, then retry.'});}});
 app.get('/api/learning/video-progress',async(req,res)=>{try{const filter={userId:req.authUserId};if(req.query.topic)filter.topic=String(req.query.topic).slice(0,250);const progress=await Progress.find(filter).sort({updatedAt:-1}).limit(1000).lean();res.json({progress});}catch(e){res.status(503).json({error:'Saved video progress is temporarily unavailable.'});}});
 app.post('/api/learning/video-progress',async(req,res)=>{try{
  const b=req.body,userId=req.authUserId;
  if(!userId)return res.status(401).json({error:'Sign in first.'});
  if(!VIDEO_ID.test(b.videoId||'')||typeof b.topic!=='string'||!b.topic.trim()||b.topic.length>250||typeof b.lessonKey!=='string'||!b.lessonKey||b.lessonKey.length>160||!Number.isFinite(b.duration)||b.duration<=0||b.duration>86400||!Number.isFinite(b.position)||!Array.isArray(b.ranges)||b.ranges.length>30||b.ranges.some(p=>!Array.isArray(p)||p.length!==2||!p.every(Number.isFinite)||p[1]-p[0]>30||p[1]<=p[0]))return res.status(400).json({error:'Invalid video progress.'});
  const filter={userId,topic:b.topic,lessonKey:b.lessonKey};const lock=crypto.createHash('sha256').update(JSON.stringify(filter)).digest('hex');
  const doc=await locked(lock,async()=>{let old=await Progress.findOne(filter).lean();if(old&&old.videoId!==b.videoId)old=null;
   const coverage=mergeCoverage(old?.coverage||[],b.ranges,b.duration);const watchedSeconds=coverage.reduce((n,[a,c])=>n+c-a,0);const watchPercent=Math.min(100,100*watchedSeconds/b.duration);
   return Progress.findOneAndUpdate(filter,{$set:{concept:String(b.concept||'').slice(0,250),videoId:b.videoId,title:String(b.title||'').slice(0,300),url:`https://www.youtube.com/watch?v=${b.videoId}`,duration:b.duration,position:Math.min(b.duration,Math.max(0,b.position)),coverage,watchedSeconds,watchPercent,completed:watchPercent>=90}},{upsert:true,new:true});});
  res.json({progress:doc,evidence:'browser_reported_watch_activity',masteryChanged:false});
 }catch(e){res.status(503).json({error:'Video progress could not be saved. Keep this lesson open and retry.'});}});
 return {Progress};
}
module.exports={installVideoFlow,rankVideos,mergeCoverage,seconds};
