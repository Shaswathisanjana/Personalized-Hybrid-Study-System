'use strict';
const {spawn}=require('node:child_process');const fs=require('node:fs/promises');const os=require('node:os');const path=require('node:path');
// Constant program only; all lesson text is JSON on stdin, never shell source.
const WINDOWS_SCRIPT=`$ErrorActionPreference='Stop'
[Console]::InputEncoding = New-Object System.Text.UTF8Encoding
Add-Type -AssemblyName System.Speech
$p = [Console]::In.ReadToEnd() | ConvertFrom-Json
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
 $voices = @($s.GetInstalledVoices() | Where-Object { $_.Enabled -and $_.VoiceInfo.Culture.Name.StartsWith('en') })
 if ($voices.Count -eq 0) { throw 'No installed English speech voice was found.' }
 $s.SelectVoice($voices[0].VoiceInfo.Name)
 $s.Rate = -1
 $s.Volume = 100
 $format = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo -ArgumentList 16000,([System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen),([System.Speech.AudioFormat.AudioChannel]::Mono)
 $i=0
 foreach ($text in $p.texts) {
  $file = Join-Path ([string]$p.directory) ('scene-'+$i+'.wav')
  $s.SetOutputToWaveFile($file,$format)
  $s.Speak([string]$text)
  $s.SetOutputToNull()
  $i++
 }
 Write-Output 'ok'
} finally { $s.Dispose() }`;
function validateTexts(value){if(!Array.isArray(value)||value.length<1||value.length>8||value.some(t=>typeof t!=='string'||!t.trim()||t.length>1400))throw Error('Provide 1–8 narration scenes of at most 1400 characters each.');return value.map(t=>t.trim());}
function runWindows(payload,spawnImpl=spawn){return new Promise((resolve,reject)=>{const child=spawnImpl('powershell.exe',['-NoProfile','-NonInteractive','-EncodedCommand',Buffer.from(WINDOWS_SCRIPT,'utf16le').toString('base64')],{windowsHide:true,stdio:['pipe','pipe','pipe']});let stderr='',settled=false;const finish=(err)=>{if(settled)return;settled=true;clearTimeout(timer);err?reject(err):resolve();};const timer=setTimeout(()=>{child.kill();finish(Error('Narration generation timed out. Try fewer scenes.'));},120000);child.on('error',()=>finish(Error('Windows speech synthesis could not start. Check that Windows PowerShell and an English speech voice are installed.')));child.stderr.on('data',d=>{stderr=(stderr+d.toString()).slice(-2500);});child.stdout.on('data',()=>{});child.on('close',code=>finish(code===0?null:Error('Windows narration failed. Check your installed English speech voice. '+stderr.replace(/\s+/g,' ').slice(0,350))));child.stdin.on('error',()=>{});child.stdin.end(JSON.stringify(payload),'utf8');});}
async function synthesize(texts,{platform=process.platform,run=runWindows}={}){validateTexts(texts);if(platform!=='win32')throw Error('Recorded narration currently requires the backend to run on Windows with an installed English voice. No silent video has been substituted.');const dir=await fs.mkdtemp(path.join(os.tmpdir(),'phss-narration-'));try{await run({directory:dir,texts});const clips=[];for(let i=0;i<texts.length;i++){const audio=await fs.readFile(path.join(dir,`scene-${i}.wav`));if(audio.length<44||audio.toString('ascii',0,4)!=='RIFF')throw Error('Speech synthesis returned an invalid audio file.');clips.push({audio:audio.toString('base64'),mimeType:'audio/wav'});}return clips;}finally{await fs.rm(dir,{recursive:true,force:true});}}
function installNarration({app,speech=synthesize}){const active=new Set();app.post('/api/learning/video/narration',async(req,res)=>{const id=req.authUserId;if(!id)return res.status(401).json({error:'Sign in before generating narration.'});if(active.has(id)||active.size>=2)return res.status(429).json({error:'Narration is already being generated. Wait for the current request to finish.'});let texts;try{texts=validateTexts(req.body.texts);}catch(e){return res.status(400).json({error:e.message});}active.add(id);try{res.set('Cache-Control','no-store');res.json({clips:await speech(texts),voice:'Installed Windows English voice',audioIncluded:true});}catch(e){res.status(503).json({error:e.message});}finally{active.delete(id);}});}
module.exports={installNarration,validateTexts,synthesize,runWindows,WINDOWS_SCRIPT};
