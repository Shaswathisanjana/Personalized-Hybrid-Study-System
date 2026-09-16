const path = require('path');
const dotenv = require('dotenv');

// Load environment variables from current directory and parent directory
dotenv.config();
dotenv.config({ path: path.resolve(__dirname, '..', '.env') });

const express = require('express');
const multer = require('multer');
const pdfParse = require('pdf-parse');
const axios = require('axios');
const cors = require('cors');
const fs = require('fs');
const { exec } = require('child_process');
const ffmpeg = require('fluent-ffmpeg');
const sharp = require('sharp');
const { GoogleGenAI } = require('@google/genai');
const Groq = require('groq-sdk');
const { mathjax } = require('mathjax-full/js/mathjax.js');
const { TeX } = require('mathjax-full/js/input/tex.js');
const { SVG } = require('mathjax-full/js/output/svg.js');
const { liteAdaptor } = require('mathjax-full/js/adaptors/liteAdaptor.js');
const { RegisterHTMLHandler } = require('mathjax-full/js/handlers/html.js');

try {
    const ffmpegPath = require('@ffmpeg-installer/ffmpeg').path;
    ffmpeg.setFfmpegPath(ffmpegPath);
} catch (e) {
    // System ffmpeg fallback
}

const app = express();
const PORT = process.env.PORT || 5000;

// MathJax setup
const mathAdaptor = liteAdaptor();
RegisterHTMLHandler(mathAdaptor);
const mathDocument = mathjax.document('', {
    InputJax: new TeX({ packages: ['base', 'ams'] }),
    OutputJax: new SVG({ fontCache: 'none' })
});

app.use(cors());
app.use(express.json());

const uploadDir = path.join(__dirname, 'uploads');
const outputDir = path.join(__dirname, 'output');
if (!fs.existsSync(uploadDir)) fs.mkdirSync(uploadDir);
if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir);

app.use('/static', express.static(outputDir));
const upload = multer({ dest: uploadDir });

const runCommand = (cmd) => new Promise((resolve, reject) => {
    exec(cmd, (err, stdout, stderr) => (err ? reject(stderr || err) : resolve(stdout)));
});

function cleanPlainText(text) {
    if (!text) return '';
    return text
        .replace(/\\text\{([^}]+)\}/g, '$1')
        .replace(/\\mathbb\{([^}]+)\}/g, '$1')
        .replace(/\\mathbf\{([^}]+)\}/g, '$1')
        .replace(/\\[a-zA-Z]+/g, ' ')
        .replace(/[{}$^_\\|]/g, '')
        .replace(/\s+/g, ' ')
        .trim();
}

function wrapText(text, maxCharsPerLine = 68, maxLines = 4) {
    const words = (text || '').split(' ');
    const lines = [];
    let currentLine = '';

    for (const word of words) {
        if ((currentLine + ' ' + word).trim().length <= maxCharsPerLine) {
            currentLine = (currentLine + ' ' + word).trim();
        } else {
            lines.push(currentLine);
            currentLine = word;
            if (lines.length === maxLines - 1) break;
        }
    }
    if (currentLine && lines.length < maxLines) lines.push(currentLine);
    return lines;
}

function renderConceptAsSvg(concept) {
    try {
        let formula = (concept || '').trim();
        if (!/[\\_{}^=><]/.test(formula)) formula = `\\text{${formula}}`;
        
        const node = mathDocument.convert(formula, { display: true });
        let svg = mathAdaptor.outerHTML(node)
            .replace(/^<mjx-container[^>]*>/, '')
            .replace(/<\/mjx-container>$/, '')
            .replace(/style="[^"]*"/, 'style="color: #9a3412;"');

        return `<g transform="translate(80, 140) scale(1.3)">${svg}</g>`;
    } catch (error) {
        const escaped = cleanPlainText(concept).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        return `<text x="80" y="180" fill="#9a3412" font-size="22" font-family="Georgia, serif">${escaped}</text>`;
    }
}

async function checkYouTubeCoverage(query) {
    try {
        const url = `https://www.youtube.com/results?search_query=${encodeURIComponent(query)}`;
        const res = await axios.get(url, { headers: { 'User-Agent': 'Mozilla/5.0' }, timeout: 6000 });
        const matches = res.data.match(/"title":{"runs":\[{"text":"(.*?)"}\]/g) || [];
        const titles = matches.map(m => m.replace(/"title":{"runs":\[{"text":"|"/g, '')).slice(0, 3);
        return { hasCoverage: titles.length > 3, titles };
    } catch {
        return { hasCoverage: false, titles: [] };
    }
}

// AGENT 1: Gemini Deep Paper Synthesis
async function runGeminiAnalysis(pdfText, apiKey) {
    const ai = new GoogleGenAI({ apiKey: apiKey.trim() });
    
    const prompt = `You are a Senior University Professor known for making difficult research concepts easy to understand.
Analyze this research paper text and extract its core concepts.

Return ONLY a valid raw JSON object with:
- "topic_title": Concise title (e.g. 'K-SVD: Overcomplete Dictionary Learning')
- "plain_english_analogy": A simple, vivid everyday real-world analogy explaining the core problem and solution to a high-school student.
- "prerequisites": Array of 2-3 foundational concepts needed to understand the paper (e.g., Matrix Multiplication, SVD).
- "mathematical_problem": The core optimization objective function in standard LaTeX.
- "algorithm_steps": Array of key sequential algorithmic steps.
- "real_world_impact": Where this is applied in practice (e.g., image denoising, compression).

Paper Content:
${pdfText.slice(0, 16000)}`;

    const response = await ai.models.generateContent({
        model: 'gemini-3.1-flash-lite-preview',
        contents: prompt,
        config: { responseMimeType: 'application/json' }
    });

    return JSON.parse(response.text.replace(/```json\n?|```/g, '').trim());
}

// Fallback Helper for Storyboarding using Gemini
async function runGeminiStoryboard(analysisData, geminiKey) {
    const ai = new GoogleGenAI({ apiKey: geminiKey.trim() });
    
    const systemPrompt = `You are an elite professor teaching beginners who have never read this research paper before.
Structure the 4-slide lecture as follows:
- Slide 1: "The Core Motivation & Intuitive Analogy" (Explain what problem this solves in plain English without complex math).
- Slide 2: "Prerequisites & Core Objective" (Define foundational terms and the main optimization goal).
- Slide 3: "The Core Mathematical Mechanism" (Step-by-step breakdown of the central formula/algorithm).
- Slide 4: "Why It Works & Real-World Impact" (Convergence, benefits, and practical applications).

Always define every symbol as if explaining to an undergraduate student.

Return ONLY valid JSON matching this schema:
{
  "storyboard": [
    {
      "title": "Slide Title",
      "concept": "LaTeX equation or core insight",
      "terms_breakdown": [
        {"term": "Symbol", "definition": "Intuitive beginner definition"}
      ],
      "narration": "2-3 clear spoken sentences explaining the intuition and math."
    }
  ]
}`;

    const userPrompt = `Generate the 4-slide educational storyboard for this paper:
Title: ${analysisData.topic_title}
Analogy: ${analysisData.plain_english_analogy}
Prerequisites: ${JSON.stringify(analysisData.prerequisites)}
Math Formulation: ${analysisData.mathematical_problem}
Steps: ${JSON.stringify(analysisData.algorithm_steps)}`;

    const response = await ai.models.generateContent({
        model: 'gemini-3.1-flash-lite-preview',
        contents: `${systemPrompt}\n\n${userPrompt}`,
        config: { responseMimeType: 'application/json' }
    });

    const cleanJson = response.text.replace(/```json\n?|```/g, '').trim();
    const parsed = JSON.parse(cleanJson);
    return parsed.storyboard || parsed;
}

// AGENT 2: Grok/Groq Storyboarding Agent
async function runGrokStoryboard(analysisData, apiKey, geminiKeyFallback = null) {
    const cleanKey = apiKey ? apiKey.trim() : '';

    const systemPrompt = `You are an elite professor teaching beginners who have never read this research paper before.
Structure the 4-slide lecture as follows:
- Slide 1: "The Core Motivation & Intuitive Analogy" (Explain what problem this solves in plain English without complex math).
- Slide 2: "Prerequisites & Core Objective" (Define foundational terms and the main optimization goal).
- Slide 3: "The Core Mathematical Mechanism" (Step-by-step breakdown of the central formula/algorithm).
- Slide 4: "Why It Works & Real-World Impact" (Convergence, benefits, and practical applications).

Always define every symbol as if explaining to an undergraduate student.

Return ONLY a valid raw JSON object with key "storyboard" containing 4 slides matching:
{
  "storyboard": [
    {
      "title": "Slide Title",
      "concept": "LaTeX formula or key conceptual equation",
      "terms_breakdown": [
        {"term": "Symbol/Concept", "definition": "Simple intuitive explanation"}
      ],
      "narration": "2-3 clear spoken sentences explaining the intuition and math."
    }
  ]
}`;

    const userPrompt = `Create the beginner-to-advanced storyboard for: ${analysisData.topic_title}.
Paper Data: ${JSON.stringify(analysisData)}`;

    if (cleanKey.startsWith('gsk_')) {
        try {
            const groq = new Groq({ apiKey: cleanKey });
            const modelListResponse = await groq.models.list();
            const availableModels = modelListResponse.data.map(m => m.id);

            const preferredModels = ['openai/gpt-oss-120b', 'openai/gpt-oss-20b', 'qwen/qwen3.6-27b', 'allam-2-7b'];
            const selectedModel = preferredModels.find(m => availableModels.includes(m)) || 'openai/gpt-oss-120b';

            const chatCompletion = await groq.chat.completions.create({
                messages: [
                    { role: 'system', content: systemPrompt },
                    { role: 'user', content: userPrompt }
                ],
                model: selectedModel,
                temperature: 0.2
            });

            const rawContent = chatCompletion.choices[0].message.content;
            const jsonMatch = rawContent.match(/\{[\s\S]*\}/);
            if (!jsonMatch) throw new Error("JSON parse error from Groq response");
            const parsed = JSON.parse(jsonMatch[0]);
            return parsed.storyboard || parsed;
        } catch (err) {
            console.warn('Groq error, switching directly to Gemini:', err.message);
            if (geminiKeyFallback) return await runGeminiStoryboard(analysisData, geminiKeyFallback);
            throw err;
        }
    }

    if (geminiKeyFallback) return await runGeminiStoryboard(analysisData, geminiKeyFallback);
    throw new Error('No valid API keys configured.');
}

// AGENT 3: Slide Generator & Video Builder
async function buildVideo(storyboard, workDir) {
    const videoSegments = [];
    const slides = Array.isArray(storyboard) ? storyboard : (storyboard.storyboard || []);

    for (let i = 0; i < slides.length; i++) {
        const slide = slides[i];
        const audioPath = path.join(workDir, `audio_${i}.mp3`);
        const imgPath = path.join(workDir, `slide_${i}.png`);
        const segmentVideoPath = path.join(workDir, `segment_${i}.mp4`);

        const cleanNarration = cleanPlainText(slide.narration);
        console.log(`[Slide ${i + 1}/${slides.length}] Synthesizing TTS Audio: "${cleanNarration.slice(0, 45)}..."`);
        await runCommand(`edge-tts --voice en-US-ChristopherNeural --text "${cleanNarration.replace(/["`$]/g, '')}" --write-media "${audioPath}"`);

        const titleText = (slide.title || `Slide ${i + 1}`).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        const conceptSvg = renderConceptAsSvg(slide.concept || '');
        const narrationLines = wrapText(cleanNarration, 72, 3);
        const narrationTspans = narrationLines.map((line, idx) => 
            `<tspan x="70" dy="${idx === 0 ? 0 : 34}">${line.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</tspan>`
        ).join('');

        const terms = (slide.terms_breakdown || []).slice(0, 4);
        let termsSvgElements = '';
        terms.forEach((t, idx) => {
            const yPos = 320 + (idx * 30);
            const safeTerm = (t.term || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            const safeDef = (t.definition || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            termsSvgElements += `
            <text x="70" y="${yPos}" fill="#9a3412" font-size="19" font-family="monospace" font-weight="bold">${safeTerm}:</text>
            <text x="210" y="${yPos}" fill="#374151" font-size="18" font-family="Arial, sans-serif">${safeDef}</text>`;
        });

        const svgBuffer = Buffer.from(`
        <svg width="1280" height="720" xmlns="http://www.w3.org/2000/svg">
            <rect width="100%" height="100%" fill="#fcf6f0"/>
            <rect x="0" y="0" width="1280" height="85" fill="#f5dfd3"/>
            <line x1="0" y1="85" x2="1280" y2="85" stroke="#e6baaa" stroke-width="2"/>
            <text x="60" y="55" fill="#1e1b18" font-size="30" font-family="Georgia, serif" font-weight="bold">${titleText}</text>
            
            <rect x="60" y="105" width="1160" height="150" rx="10" fill="#ffffff" stroke="#c05640" stroke-width="2"/>
            ${conceptSvg}

            <rect x="60" y="270" width="1160" height="175" rx="10" fill="#ffffff" stroke="#d69a82" stroke-width="1.5"/>
            <text x="70" y="295" fill="#9a3412" font-size="14" font-family="Arial, sans-serif" font-weight="bold" letter-spacing="1">VARIABLE &amp; CONCEPT BREAKDOWN</text>
            ${termsSvgElements}

            <rect x="60" y="460" width="1160" height="225" rx="10" fill="#fffaf7" stroke="#e0b29f" stroke-width="1.5"/>
            <text x="70" y="490" fill="#9a3412" font-size="14" font-family="Arial, sans-serif" font-weight="bold" letter-spacing="1">INTUITIVE EXPLANATION</text>
            <text x="70" y="535" fill="#1f2937" font-size="22" font-family="Georgia, serif">
                ${narrationTspans}
            </text>
        </svg>`);

        await sharp(svgBuffer).png().toFile(imgPath);

        console.log(`[Slide ${i + 1}/${slides.length}] Encoding Segment MP4...`);
        await new Promise((resolve, reject) => {
            ffmpeg()
                .input(imgPath)
                .loop()
                .input(audioPath)
                .outputOptions(['-c:v libx264', '-tune stillimage', '-c:a aac', '-b:a 192k', '-pix_fmt yuv420p', '-shortest'])
                .save(segmentVideoPath)
                .on('end', resolve)
                .on('error', (err) => {
                    console.error(`FFmpeg Segment ${i} Error:`, err);
                    reject(err);
                });
        });

        videoSegments.push(segmentVideoPath);
    }

    console.log('[Concatenation] Merging segments into final lecture video...');
    const listFilePath = path.join(workDir, 'concat_list.txt');
    const listContent = videoSegments.map(seg => `file '${seg.replace(/\\/g, '/')}'`).join('\n');
    fs.writeFileSync(listFilePath, listContent);

    const finalVideoName = `output_${Date.now()}.mp4`;
    const finalVideoPath = path.join(outputDir, finalVideoName);

    await new Promise((resolve, reject) => {
        ffmpeg()
            .input(listFilePath)
            .inputOptions(['-f concat', '-safe 0'])
            .outputOptions(['-c copy'])
            .save(finalVideoPath)
            .on('end', resolve)
            .on('error', reject);
    });

    console.log(`[Success] Video generated: ${finalVideoName}`);
    return `/static/${finalVideoName}`;
}

// In-Memory cache for the current paper context to power interactive Q&A
let lastAnalyzedPaper = {
    title: '',
    fullText: '',
    analysis: null
};

app.get('/api/env-status', (req, res) => {
    res.json({
        hasGeminiEnv: !!(process.env.GEMINI_API_KEY || process.env.GEMINI_KEY),
        hasGrokEnv: !!(process.env.GROQ_API_KEY || process.env.GROK_API_KEY || process.env.XAI_API_KEY || process.env.GROK_KEY)
    });
});

// INTERACTIVE Q&A ENDPOINT: "Ask AI Professor"
app.post('/api/ask-question', async (req, res) => {
    try {
        const { question, geminiKey } = req.body;
        const key = (geminiKey || process.env.GEMINI_API_KEY || process.env.GEMINI_KEY || '').trim();

        if (!question) return res.status(400).json({ error: 'Question is required.' });
        if (!key) return res.status(400).json({ error: 'Gemini API key is required.' });

        const ai = new GoogleGenAI({ apiKey: key });
        const prompt = `You are a supportive, encouraging computer science and math professor answering a student's question about the research paper "${lastAnalyzedPaper.title || 'the uploaded paper'}".

Paper Summary & Context:
${JSON.stringify(lastAnalyzedPaper.analysis || {})}

Paper Excerpt:
${(lastAnalyzedPaper.fullText || '').slice(0, 10000)}

Student Question:
"${question}"

Instructions for your response:
1. Explain in simple, intuitive terms suitable for a beginner.
2. Use a relatable real-world analogy if possible.
3. If math is required, break down the intuition first before showing symbols.
4. Keep the response concise, clear, and direct (under 200 words).`;

        const response = await ai.models.generateContent({
            model: 'gemini-3.1-flash-lite-preview',
            contents: prompt
        });

        res.json({ answer: response.text });
    } catch (err) {
        console.error('Q&A Error:', err);
        res.status(500).json({ error: err.message || 'Could not answer question.' });
    }
});

// MAIN GENERATION PIPELINE
app.post('/api/generate-video', upload.single('pdf'), async (req, res) => {
    let pdfPath = null;
    try {
        const geminiKey = (req.body.geminiKey || process.env.GEMINI_API_KEY || process.env.GEMINI_KEY || '').trim();
        const grokKey = (req.body.grokKey || process.env.GROQ_API_KEY || process.env.GROK_API_KEY || process.env.XAI_API_KEY || process.env.GROK_KEY || '').trim();
        const pdfFile = req.file;

        if (!pdfFile) return res.status(400).json({ error: 'Please upload a PDF file.' });
        pdfPath = pdfFile.path;

        if (!geminiKey) return res.status(400).json({ error: 'Gemini API Key is required.' });

        console.log('[1/4] Parsing PDF...');
        const dataBuffer = fs.readFileSync(pdfPath);
        const parsedPdf = await pdfParse(dataBuffer);

        console.log('[2/4] Running Beginner-First Pedagogical Analysis with Gemini...');
        const analysis = await runGeminiAnalysis(parsedPdf.text, geminiKey);
        
        // Cache paper for live Q&A
        lastAnalyzedPaper = {
            title: analysis.topic_title,
            fullText: parsedPdf.text,
            analysis: analysis
        };

        console.log('[3/4] Generating 4-Stage Progressive Storyboard...');
        const ytStatus = await checkYouTubeCoverage(analysis.topic_title);
        const storyboard = await runGrokStoryboard(analysis, grokKey, geminiKey);

        console.log('[4/4] Building Multi-Panel Explanatory Video...');
        const workDir = fs.mkdtempSync(path.join(__dirname, 'tmp-'));
        const videoUrl = await buildVideo(storyboard, workDir);

        if (fs.existsSync(pdfPath)) fs.unlinkSync(pdfPath);

        res.json({
            videoUrl,
            analysis,
            youtubeCoverage: ytStatus,
            storyboard
        });
    } catch (err) {
        console.error('--- Pipeline Execution Error ---');
        console.error(err);
        if (pdfPath && fs.existsSync(pdfPath)) fs.unlinkSync(pdfPath);
        res.status(500).json({ error: err.message || 'Pipeline failed during processing.' });
    }
});

// EMBEDDED REACT UI WITH INTERACTIVE "ASK AI" ASSISTANT
app.use((req, res) => {
    res.send(`
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Paper-to-Video AI Studio</title>
  <style>
    body { margin: 0; min-height: 100vh; background: #f7d6c6; color: #111827; font-family: Georgia, 'Times New Roman', serif; }
    .container { max-width: 980px; margin: 0 auto; padding: 44px 28px 70px; }
    .hero { display: flex; justify-content: space-between; gap: 24px; align-items: end; margin-bottom: 28px; }
    .eyebrow { color: #9a3412; font: 700 12px/1.2 Arial, sans-serif; letter-spacing: 2px; text-transform: uppercase; }
    h1 { margin: 8px 0 10px; font-size: clamp(32px, 5vw, 56px); line-height: 1; }
    .intro { max-width: 610px; margin: 0; color: #4b3832; font: 17px/1.6 Arial, sans-serif; }
    .panel { background: #fff1ea; border: 1px solid #d69a82; border-radius: 16px; padding: 24px; box-shadow: 0 18px 50px #7c3f2b33; }
    .steps { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 22px; }
    .step { color: #9b8177; font: 700 12px Arial, sans-serif; border-bottom: 3px solid #e3b8a6; padding-bottom: 10px; }
    .step.active { color: #9a3412; border-color: #c05640; }
    .dropzone { display: grid; place-items: center; min-height: 130px; text-align: center; border: 2px dashed #c77d63; border-radius: 12px; background: #fffaf7; cursor: pointer; transition: .2s ease; }
    .dropzone:hover, .dropzone.dragging { border-color: #9a3412; background: #ffe4d6; transform: translateY(-1px); }
    .dropzone strong { display: block; color: #111827; font: 700 18px Arial, sans-serif; }
    .dropzone span { display: block; margin-top: 8px; color: #6b5148; font: 14px Arial, sans-serif; }
    .file-name { margin-top: 10px; color: #9a3412; font: 700 14px Arial, sans-serif; }
    label { display: block; margin-top: 20px; color: #111827; font: 700 14px Arial, sans-serif; }
    input[type="text"], input[type="password"], input[type="file"] {
      width: 100%; box-sizing: border-box; padding: 12px; margin-top: 6px; margin-bottom: 16px;
      background: #fffaf7; border: 1px solid #c99a88; border-radius: 8px; color: #111827; font: 15px Arial, sans-serif;
    }
    .badge { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-left: 8px; }
    .badge-ok { background: #dcfce7; color: #166534; }
    button {
      width: 100%; margin-top: 24px; padding: 16px; background: #c05640; border: none; border-radius: 8px;
      color: #fffaf7; font: 700 16px Arial, sans-serif; cursor: pointer; transition: .2s ease;
    }
    button:hover:not(:disabled) { background: #9a3412; transform: translateY(-1px); }
    button:disabled { background: #64748b; cursor: not-allowed; }
    .status { display: flex; align-items: center; gap: 10px; margin: 18px 0 0; color: #9a3412; font: 14px Arial, sans-serif; }
    .status-dot { width: 9px; height: 9px; border-radius: 50%; background: #c05640; box-shadow: 0 0 0 5px #c0564025; animation: pulse 1.2s infinite; }
    .card { background: #fffaf7; padding: 24px; border-radius: 12px; margin-top: 28px; border: 1px solid #d69a82; }
    .card h2 { font-size: 30px; margin-bottom: 18px; }
    .card h3 { color: #9a3412; font: 700 20px Arial, sans-serif; margin-top: 18px; }
    .card p { color: #30231f; font: 16px/1.6 Arial, sans-serif; }
    .analogy-box { background: #ffe4d6; border-left: 5px solid #c05640; padding: 14px 18px; border-radius: 0 8px 8px 0; font: 16px/1.6 Arial, sans-serif; color: #431407; margin: 15px 0; }
    
    /* Q&A Section Styling */
    .qa-box { background: #ffffff; border: 2px solid #e0b29f; border-radius: 12px; padding: 20px; margin-top: 24px; }
    .qa-box h4 { margin: 0 0 10px; color: #9a3412; font-size: 20px; font-family: Arial, sans-serif; }
    .qa-input-row { display: flex; gap: 10px; }
    .qa-input-row input { margin: 0; flex: 1; }
    .qa-input-row button { margin: 0; width: auto; padding: 12px 24px; white-space: nowrap; }
    .qa-answer { margin-top: 16px; background: #fffaf7; border-left: 4px solid #166534; padding: 12px 16px; border-radius: 4px; font: 16px/1.6 Arial, sans-serif; color: #1f2937; }
    
    @keyframes pulse { 50% { opacity: .35; transform: scale(.8); } }
  </style>
</head>
<body>
  <main class="container">
    <header class="hero"><div><div class="eyebrow">Beginner-Friendly AI Lectures</div><h1>Paper to Video</h1><p class="intro">Turns any complex paper into a progressive visual lecture: Real-world Analogy &rarr; Prerequisites &rarr; Equations &rarr; Applications.</p></div></header>
    <section class="panel">
      <div class="steps"><div id="step-upload" class="step active">01 &nbsp; UPLOAD PAPER</div><div id="step-ai" class="step">02 &nbsp; DEEP EXPLANATION</div><div id="step-watch" class="step">03 &nbsp; WATCH &amp; ASK</div></div>
      <label>Research paper (PDF)</label>
      <div id="dropzone" class="dropzone"><div><strong>Drop your PDF here</strong><span>or click to browse your files</span><div id="file-name" class="file-name"></div></div></div>
      <input id="pdf-input" type="file" accept="application/pdf" style="display:none" />
      <label>Gemini API Key <span id="gemini-badge"></span></label>
      <input id="gemini-key" type="password" placeholder="Enter Gemini API Key" />
      <label>Grok (xAI) / Groq API Key <span id="grok-badge"></span></label>
      <input id="grok-key" type="password" placeholder="Enter Grok/Groq API Key" />
      <button id="generate-button" type="button">Generate Beginner-Friendly Lecture</button>
      <div id="status" class="status" hidden><span class="status-dot"></span><span id="status-text"></span></div>
      <section id="result" class="card" hidden></section>
    </section>
  </main>
  <script>
    const $ = (id) => document.getElementById(id);
    let selectedFile = null;
    const setFile = (file) => {
      if (!file || file.type !== 'application/pdf') return alert('Please choose a PDF research paper.');
      selectedFile = file;
      $('file-name').textContent = 'Selected: ' + file.name;
    };
    $('dropzone').onclick = () => $('pdf-input').click();
    $('pdf-input').onchange = (event) => setFile(event.target.files[0]);
    $('dropzone').ondragover = (event) => { event.preventDefault(); $('dropzone').classList.add('dragging'); };
    $('dropzone').ondragleave = () => $('dropzone').classList.remove('dragging');
    $('dropzone').ondrop = (event) => { event.preventDefault(); $('dropzone').classList.remove('dragging'); setFile(event.dataTransfer.files[0]); };
    
    fetch('/api/env-status').then((response) => response.json()).then((data) => {
      if (data.hasGeminiEnv) $('gemini-badge').innerHTML = '<span class="badge badge-ok">Detected in .env</span>';
      if (data.hasGrokEnv) $('grok-badge').innerHTML = '<span class="badge badge-ok">Detected in .env</span>';
    }).catch(() => {});
    
    $('generate-button').onclick = async () => {
      if (!selectedFile) return alert('Please select a PDF file to upload.');
      const button = $('generate-button');
      button.disabled = true; button.textContent = 'Deconstructing Mathematics & Rendering...'; $('status').hidden = false;
      $('status-text').textContent = 'Generating real-world analogies, building progressive slides, and synthesizing voiceover...'; $('step-ai').classList.add('active'); $('result').hidden = true;
      const formData = new FormData(); formData.append('pdf', selectedFile); formData.append('geminiKey', $('gemini-key').value); formData.append('grokKey', $('grok-key').value);
      try {
        const response = await fetch('/api/generate-video', { method: 'POST', body: formData }); const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Video creation failed.');
        $('step-watch').classList.add('active');
        
        $('result').innerHTML = \`
          <h2>🎥 Generated Video Lecture</h2>
          <video width="100%" controls style="border-radius:8px">
            <source src="\${data.videoUrl}" type="video/mp4">
          </video>
          
          <h3>📖 Topic: \${data.analysis.topic_title}</h3>
          
          <div class="analogy-box">
            <strong>💡 Plain English Analogy for Beginners:</strong><br/>
            \${data.analysis.plain_english_analogy}
          </div>

          <p><strong>🔑 Prerequisites to Know:</strong> \${(data.analysis.prerequisites || []).join(', ')}</p>
          <p><strong>🌐 Practical Applications:</strong> \${data.analysis.real_world_impact || 'Research and engineering'}</p>

          <div class="qa-box">
            <h4>💬 Still Confused? Ask the AI Professor:</h4>
            <p style="margin: 4px 0 12px; color: #6b7280; font-size: 14px;">Ask anything you didn't understand in the video (e.g. "What is an atom in this paper?"):</p>
            <div class="qa-input-row">
              <input id="qa-question-input" type="text" placeholder="Type your question in plain words..." />
              <button id="qa-ask-button" type="button">Ask</button>
            </div>
            <div id="qa-answer-container" class="qa-answer" hidden></div>
          </div>
        \`;
        
        $('result').hidden = false;

        // Attach event listener to the live Q&A assistant
        $('qa-ask-button').onclick = async () => {
          const qInput = $('qa-question-input');
          const ansContainer = $('qa-answer-container');
          if (!qInput.value.trim()) return;

          $('qa-ask-button').disabled = true;
          $('qa-ask-button').textContent = 'Thinking...';
          ansContainer.hidden = false;
          ansContainer.textContent = 'Professor is writing an intuitive explanation...';

          try {
            const qaRes = await fetch('/api/ask-question', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                question: qInput.value,
                geminiKey: $('gemini-key').value
              })
            });
            const qaData = await qaRes.json();
            if (!qaRes.ok) throw new Error(qaData.error || 'Failed to get answer');
            ansContainer.innerHTML = '<strong>Answer:</strong> ' + qaData.answer;
          } catch (e) {
            ansContainer.textContent = 'Error: ' + e.message;
          } finally {
            $('qa-ask-button').disabled = false;
            $('qa-ask-button').textContent = 'Ask';
          }
        };

      } catch (error) { 
        alert('Error: ' + error.message); 
      } finally { 
        button.disabled = false; 
        button.textContent = 'Generate Beginner-Friendly Lecture'; 
        $('status').hidden = true; 
      }
    };
  </script>
</body>
</html>
    `);
});

app.listen(PORT, () => console.log(`Server running at http://localhost:${PORT}`));
