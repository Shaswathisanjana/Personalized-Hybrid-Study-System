require('dotenv').config();
const express = require('express');
const mongoose = require('mongoose');
const axios = require('axios');
const path = require('path');

const { ChatGoogleGenerativeAI } = require('@langchain/google-genai');
const { StateGraph, END, START, Annotation } = require('@langchain/langgraph');
const { SystemMessage, HumanMessage } = require('@langchain/core/messages');

const app = express();
app.use(express.json());

// ==========================================
// 1. MONGODB MODELS (Learning History & Progress)
// ==========================================
const UserProgressSchema = new mongoose.Schema({
  userId: { type: String, default: 'user_default' },
  videoId: String,
  title: String,
  currentTime: { type: Number, default: 0 },
  duration: { type: Number, default: 0 },
  completed: { type: Boolean, default: false },
  lastWatchedAt: { type: Date, default: Date.now },
});

const LearningHistorySchema = new mongoose.Schema({
  userId: { type: String, default: 'user_default' },
  topic: String,
  completedVideos: [String],
  quizScores: [{ topic: String, score: Number, total: Number, date: Date }],
  aiNotes: String,
});

const UserProgress = mongoose.model('UserProgress', UserProgressSchema);
const LearningHistory = mongoose.model('LearningHistory', LearningHistorySchema);

// Connect to MongoDB
mongoose.connect(process.env.MONGO_URI || 'mongodb://127.0.0.1:27017/ai_tutor')
  .then(() => console.log('MongoDB Connected'))
  .catch(err => console.error('MongoDB connection error:', err));

// ==========================================
// 2. LANGGRAPH AI AGENT (Gemini-Powered)
// ==========================================
const llm = new ChatGoogleGenerativeAI({
  model: 'gemini-3.1-flash-lite-preview',
  apiKey: process.env.GEMINI_API_KEY,
  temperature: 0.7,
});

// Define Agent State
const AgentState = Annotation.Root({
  userIntent: Annotation(),
  topic: Annotation(),
  historyContext: Annotation(),
  recommendations: Annotation(),
  quiz: Annotation(),
});

// Node 1: Fetch Learner History
async function fetchHistoryNode(state) {
  const history = await LearningHistory.findOne({ userId: 'user_default' }) || {};
  const progress = await UserProgress.find({ userId: 'user_default' });
  
  const historyContext = `
    Completed Topics: ${JSON.stringify(history.topic || [])}
    Recent Progress: ${JSON.stringify(progress.map(p => ({ title: p.title, completed: p.completed })))}
  `;
  return { historyContext };
}

// Node 2: Analyze Next Lesson or Generate Quiz
async function decisionNode(state) {
  if (state.userIntent === 'GENERATE_QUIZ') {
    const prompt = `Based on the topic "${state.topic}", generate a 3-question multiple-choice quiz in valid JSON format:
    {"questions": [{"question": "...", "options": ["A", "B", "C", "D"], "answer": "A"}]}`;
    
    const response = await llm.invoke([new SystemMessage("You are an educational AI assistant."), new HumanMessage(prompt)]);
    let quizData;
    try {
      quizData = JSON.parse(response.content.replace(/```json|```/g, '').trim());
    } catch (e) {
      quizData = { error: "Failed to parse quiz format" };
    }
    return { quiz: quizData };
  } else {
    const prompt = `Learner state: ${state.historyContext}. The user wants to learn: "${state.topic}". 
    Suggest 3 specific search sub-topics/keywords for YouTube lessons to build a progressive learning path.
    Return JSON array of strings, e.g., ["topic 1", "topic 2", "topic 3"]`;
    
    const response = await llm.invoke([new SystemMessage("You are an adaptive curriculum planner."), new HumanMessage(prompt)]);
    let recs;
    try {
      recs = JSON.parse(response.content.replace(/```json|```/g, '').trim());
    } catch (e) {
      recs = [state.topic];
    }
    return { recommendations: recs };
  }
}

// Build StateGraph
const workflow = new StateGraph(AgentState)
  .addNode("fetchHistory", fetchHistoryNode)
  .addNode("decisionEngine", decisionNode)
  .addEdge(START, "fetchHistory")
  .addEdge("fetchHistory", "decisionEngine")
  .addEdge("decisionEngine", END);

const agentApp = workflow.compile();

// ==========================================
// 3. REST API ENDPOINTS
// ==========================================

// Search YouTube Videos via Data API
app.get('/api/youtube/search', async (req, res) => {
  const query = req.query.q || 'JavaScript tutorials';
  try {
    const url = `https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=5&q=${encodeURIComponent(query)}&type=video&key=${process.env.YOUTUBE_API_KEY}`;
    const response = await axios.get(url);
    const items = response.data.items.map(item => ({
      videoId: item.id.videoId,
      title: item.snippet.title,
      thumbnail: item.snippet.thumbnails.medium.url,
      channelTitle: item.snippet.channelTitle,
    }));
    res.json(items);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Sync Playback Progress (Live Tracking + Resume)
app.post('/api/progress/sync', async (req, res) => {
  const { videoId, title, currentTime, duration } = req.body;
  const completed = duration > 0 && (currentTime / duration) > 0.9; // 90% threshold

  const progress = await UserProgress.findOneAndUpdate(
    { userId: 'user_default', videoId },
    { title, currentTime, duration, completed, lastWatchedAt: new Date() },
    { upsert: true, new: true }
  );

  res.json({ success: true, progress });
});

// Resume Position Query
app.get('/api/progress/resume/:videoId', async (req, res) => {
  const progress = await UserProgress.findOne({ userId: 'user_default', videoId: req.params.videoId });
  res.json({ currentTime: progress ? progress.currentTime : 0 });
});

// AI Agent Endpoint: Recommendation & Next Step
app.post('/api/agent/recommend', async (req, res) => {
  const { topic } = req.body;
  const result = await agentApp.invoke({ userIntent: 'RECOMMEND', topic });
  res.json(result);
});

// AI Agent Endpoint: Generate Quiz
app.post('/api/agent/quiz', async (req, res) => {
  const { topic } = req.body;
  const result = await agentApp.invoke({ userIntent: 'GENERATE_QUIZ', topic });
  res.json(result.quiz);
});

// ==========================================
// 4. FRONTEND INTERFACE (Served Inline)
// ==========================================
app.get('/', (req, res) => {
  res.send(`
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>AI YouTube Learning Platform</title>
  <script src="https://www.youtube.com/iframe_api"></script>
  <style>
    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }
    .container { display: flex; gap: 20px; max-width: 1200px; margin: 0 auto; }
    .main { flex: 2; }
    .sidebar { flex: 1; background: #1e293b; padding: 15px; border-radius: 8px; }
    input, button { padding: 10px; margin: 5px 0; border-radius: 4px; border: none; }
    input[type="text"] { width: 70%; }
    button { background: #3b82f6; color: white; cursor: pointer; }
    button:hover { background: #2563eb; }
    .video-card { background: #334155; padding: 10px; margin: 8px 0; border-radius: 6px; cursor: pointer; }
    #player { width: 100%; height: 380px; border-radius: 8px; background: #000; }
    .quiz-box { background: #334155; padding: 15px; margin-top: 15px; border-radius: 6px; }
  </style>
</head>
<body>
  <h1>AI Learning Assistant</h1>
  <div class="container">
    <div class="main">
      <div>
        <input type="text" id="topicInput" placeholder="Enter topic to learn (e.g. LangChain basics)">
        <button onclick="searchAndRecommend()">Search & Plan</button>
      </div>
      <div id="player" style="margin-top: 15px;"></div>
      <h3 id="videoTitle">Select a video to start</h3>
      <div id="quizContainer"></div>
    </div>
    
    <div class="sidebar">
      <h3>AI Curriculum Paths</h3>
      <div id="recommendations">Run a search to get AI recommendations</div>
      <h3>Search Results</h3>
      <div id="searchResults"></div>
    </div>
  </div>

  <script>
    let player;
    let currentVideoId = '';
    let syncInterval = null;

    function onYouTubeIframeAPIReady() {}

    function loadVideo(videoId, title) {
      currentVideoId = videoId;
      document.getElementById('videoTitle').innerText = title;

      fetch('/api/progress/resume/' + videoId)
        .then(res => res.json())
        .then(data => {
          const startSeconds = data.currentTime || 0;
          if (player) {
            player.loadVideoById({ videoId: videoId, startSeconds: startSeconds });
          } else {
            player = new YT.Player('player', {
              videoId: videoId,
              playerVars: { 'start': Math.floor(startSeconds) },
              events: { 'onStateChange': onPlayerStateChange }
            });
          }
        });
    }

    function onPlayerStateChange(event) {
      if (event.data === YT.PlayerState.PLAYING) {
        startProgressTracking();
      } else {
        stopProgressTracking();
      }
      
      if (event.data === YT.PlayerState.ENDED) {
        triggerQuiz();
      }
    }

    function startProgressTracking() {
      if (syncInterval) clearInterval(syncInterval);
      syncInterval = setInterval(() => {
        if (player && player.getCurrentTime) {
          const currentTime = player.getCurrentTime();
          const duration = player.getDuration();
          
          fetch('/api/progress/sync', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              videoId: currentVideoId,
              title: document.getElementById('videoTitle').innerText,
              currentTime,
              duration
            })
          });
        }
      }, 5000); // Sync every 5 seconds
    }

    function stopProgressTracking() {
      if (syncInterval) clearInterval(syncInterval);
    }

    async function searchAndRecommend() {
      const topic = document.getElementById('topicInput').value;
      
      // Fetch AI Plan
      const agentRes = await fetch('/api/agent/recommend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic })
      });
      const agentData = await agentRes.json();
      
      const recDiv = document.getElementById('recommendations');
      recDiv.innerHTML = (agentData.decisionEngine?.recommendations || []).map(r => '<div>• ' + r + '</div>').join('');

      // Fetch YouTube Videos
      const ytRes = await fetch('/api/youtube/search?q=' + encodeURIComponent(topic));
      const videos = await ytRes.json();
      
      const searchDiv = document.getElementById('searchResults');
      searchDiv.innerHTML = videos.map(v => \`
        <div class="video-card" onclick="loadVideo('\${v.videoId}', '\${v.title.replace(/'/g, "\\'")}')">
          <strong>\${v.title}</strong><br>
          <small>\${v.channelTitle}</small>
        </div>
      \`).join('');
    }

    async function triggerQuiz() {
      const topic = document.getElementById('topicInput').value || 'Lesson';
      const res = await fetch('/api/agent/quiz', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic })
      });
      const quiz = await res.json();
      
      if (quiz.questions) {
        const quizContainer = document.getElementById('quizContainer');
        quizContainer.innerHTML = '<div class="quiz-box"><h3>Lesson Completed! AI Quiz:</h3>' + 
          quiz.questions.map((q, i) => \`
            <p><strong>Q\${i+1}: \${q.question}</strong></p>
            \${q.options.map(opt => \`<label><input type="radio" name="q\${i}" value="\${opt}"> \${opt}</label><br>\`).join('')}
          \`).join('') + '</div>';
      }
    }
  </script>
</body>
</html>
  `);
});

// Start Express Server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}`);
});