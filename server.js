require('dotenv').config();

const express = require('express');
const mongoose = require('mongoose');
const axios = require('axios');
const crypto = require('node:crypto');

const { ChatGoogleGenerativeAI } = require('@langchain/google-genai');
const {
  StateGraph,
  END,
  START,
  Annotation
} = require('@langchain/langgraph');

const {
  SystemMessage,
  HumanMessage
} = require('@langchain/core/messages');

const app = express();

app.use(express.json());


// ======================================================
// 1. MONGODB MODELS
// ======================================================

// ------------------------------------------------------
// Student Profile
// ------------------------------------------------------

const StudentSchema = new mongoose.Schema({
  userId: {
    type: String,
    unique: true,
    required: true
  },

  name: {
    type: String,
    default: ''
  },

  email: {
    type: String,
    default: undefined,
    sparse: true
  },

  createdAt: {
    type: Date,
    default: Date.now
  }
});


// ------------------------------------------------------
// Video Progress (per student, per video)
// ------------------------------------------------------

const UserProgressSchema = new mongoose.Schema({
  userId: {
    type: String,
    required: true,
    index: true
  },

  videoId: {
    type: String,
    required: true
  },

  courseId: {
    type: String,
    default: ''
  },

  courseTopic: {
    type: String,
    default: ''
  },

  lessonTitle: {
    type: String,
    default: ''
  },

  lessonIndex: {
    type: Number,
    default: 0
  },

  title: {
    type: String,
    default: ''
  },

  currentTime: {
    type: Number,
    default: 0
  },

  duration: {
    type: Number,
    default: 0
  },

  percentWatched: {
    type: Number,
    default: 0
  },

  completed: {
    type: Boolean,
    default: false
  },

  lastWatchedAt: {
    type: Date,
    default: Date.now
  }
});

// One student has exactly one progress record per video.
// This is what makes "resume" and "per-student tracking" work correctly.
UserProgressSchema.index(
  { userId: 1, courseId: 1, videoId: 1 },
  { unique: true }
);


// ------------------------------------------------------
// Learning History (per student)
// ------------------------------------------------------

const LearningHistorySchema = new mongoose.Schema({
  userId: {
    type: String,
    required: true,
    index: true
  },

  courseId: {
    type: String,
    default: () => crypto.randomUUID(),
    index: true
  },

  learningMode: {
    type: String,
    enum: ['course', 'topic'],
    default: 'topic'
  },

  courseStatus: {
    type: String,
    enum: ['active', 'completed'],
    default: 'active'
  },

  topic: {
    type: String,
    default: ''
  },

  curriculum: [
    {
      title: String,
      description: String,
      searchQuery: String,
      order: Number,
      completed: {
        type: Boolean,
        default: false
      }
    }
  ],

  currentLesson: {
    type: Number,
    default: 0
  },

  completedVideos: {
    type: [String],
    default: []
  },

  quizScores: [
    {
      topic: String,
      videoId: String,
      score: Number,
      total: Number,
      questions: mongoose.Schema.Types.Mixed,
      answers: [String],
      date: {
        type: Date,
        default: Date.now
      }
    }
  ],

  aiNotes: {
    type: String,
    default: ''
  }
});

LearningHistorySchema.index({ userId: 1, courseId: 1 }, { unique: true });


// ------------------------------------------------------
// Models
// ------------------------------------------------------

const Student = mongoose.model('Student', StudentSchema);
const UserProgress = mongoose.model('UserProgress', UserProgressSchema);
const LearningHistory = mongoose.model('LearningHistory', LearningHistorySchema);


// ======================================================
// 2. CONNECT TO MONGODB (fixed: server now waits for a
//    real connection before accepting traffic, and logs
//    connection state changes so you can see it working)
// ======================================================

const MONGO_URI = process.env.MONGO_URI || 'mongodb://127.0.0.1:27017/ai_tutor';

mongoose.connection.on('connected', () => {
  console.log(`[db] connected -> ${MONGO_URI}`);
});

mongoose.connection.on('error', (err) => {
  console.error('[db] connection error:', err.message);
});

mongoose.connection.on('disconnected', () => {
  console.warn('[db] disconnected');
});

async function connectDB() {
  try {
    await mongoose.connect(MONGO_URI);
    try {
      await Student.collection.dropIndex('email_1');
      console.log('[db] removed obsolete students.email unique index');
    } catch (indexError) {
      if (indexError.code !== 27 && indexError.codeName !== 'IndexNotFound') {
        throw indexError;
      }
    }
    for (const [collection, indexName] of [
      [LearningHistory, 'userId_1'],
      [UserProgress, 'userId_1_videoId_1']
    ]) {
      try {
        await collection.collection.dropIndex(indexName);
        console.log(`[db] removed obsolete index ${indexName}`);
      } catch (indexError) {
        if (indexError.code !== 27 && indexError.codeName !== 'IndexNotFound') {
          throw indexError;
        }
      }
    }
    const legacyCourses = await LearningHistory.find({
      $or: [{ courseId: { $exists: false } }, { courseId: null }, { courseId: '' }]
    });
    for (const legacyCourse of legacyCourses) {
      const courseId = crypto.randomUUID();
      await LearningHistory.updateOne({ _id: legacyCourse._id }, { $set: { courseId } });
      await UserProgress.updateMany(
        { userId: legacyCourse.userId, courseTopic: legacyCourse.topic, $or: [{ courseId: { $exists: false } }, { courseId: '' }] },
        { $set: { courseId } }
      );
      console.log(`[db] migrated legacy course ${legacyCourse.topic} -> ${courseId}`);
    }
    await LearningHistory.createIndexes();
    await UserProgress.createIndexes();
  } catch (err) {
    console.error('[db] initial connection failed:', err.message);
    console.error('[db] make sure MongoDB is running (check MongoDB Compass / `Get-Service -Name MongoDB`)');
    process.exit(1);
  }
}


// ======================================================
// 3. GEMINI + LANGGRAPH AI AGENT
// ======================================================

const llm = new ChatGoogleGenerativeAI({
  // NOTE: "gemini-3.1-flash-lite-preview" is not a valid model name and will
  // fail every AI call. Use a real current model instead.
  model: process.env.GEMINI_MODEL || 'gemini-2.5-flash',
  apiKey: process.env.GEMINI_API_KEY,
  temperature: 0.7
});


// ------------------------------------------------------
// LangGraph State
// ------------------------------------------------------

const AgentState = Annotation.Root({
  userId: Annotation(),
  userIntent: Annotation(),
  topic: Annotation(),
  historyContext: Annotation(),
  recommendations: Annotation(),
  quiz: Annotation()
});


// ======================================================
// NODE 1 - FETCH STUDENT HISTORY
// ======================================================

async function fetchHistoryNode(state) {
  try {
    const activeUserId = state.userId || 'user_default';

    const history = await LearningHistory.findOne({ userId: activeUserId });

    const progress = await UserProgress.find({ userId: activeUserId })
      .sort({ lastWatchedAt: -1 });

    const historyContext = `
Student ID:
${activeUserId}

Current Topic:
${history?.topic || 'No topic recorded'}

Completed Videos:
${JSON.stringify(history?.completedVideos || [])}

Recent Video Progress:
${JSON.stringify(
  progress.map((p) => ({
    videoId: p.videoId,
    title: p.title,
    completed: p.completed,
    currentTime: p.currentTime,
    duration: p.duration
  }))
)}

Previous Quiz Scores:
${JSON.stringify(history?.quizScores || [])}
`;

    return { historyContext };
  } catch (error) {
    console.error('History Node Error:', error.message);
    return { historyContext: 'No previous learning history available.' };
  }
}


// ======================================================
// NODE 2 - AI DECISION ENGINE
// ======================================================

async function decisionNode(state) {
  // ====================================================
  // QUIZ GENERATION
  // ====================================================
  if (state.userIntent === 'GENERATE_QUIZ') {
    const prompt = `
You are an educational AI assistant.

Generate a 3-question multiple-choice quiz about the following topic:

"${state.topic}"

Return ONLY valid JSON.

Required format:

{
  "questions": [
    {
      "question": "Question text",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "answer": "Option A"
    }
  ]
}

Rules:
- Exactly 3 questions.
- Exactly 4 options per question.
- "answer" must exactly match one option.
- No markdown.
- No explanation.
`;

    try {
      const response = await llm.invoke([
        new SystemMessage('You are an educational AI assistant.'),
        new HumanMessage(prompt)
      ]);

      let content = response.content;
      if (Array.isArray(content)) {
        content = content.map((item) => item.text || '').join('');
      }

      content = String(content)
        .replace(/```json/gi, '')
        .replace(/```/g, '')
        .trim();

      const quizData = JSON.parse(content);
      return { quiz: quizData };
    } catch (error) {
      console.error('Quiz generation error:', error.message);
      return { quiz: { error: 'Failed to generate quiz.' } };
    }
  }

  // ====================================================
  // COURSE ROADMAP GENERATION
  // ====================================================
  const prompt = `
You are an expert curriculum designer.

Here is the learner's history:

${state.historyContext}

The learner wants to learn:

"${state.topic}"

Create a complete, ordered course roadmap for the learner's requested subject.
Break it into the essential subtopics needed to learn the subject from foundation
to practical application. Do not include unrelated subjects.

Return ONLY a valid JSON object in this exact format:
{
  "courseTitle": "Subject course title",
  "lessons": [
    {
      "title": "One focused subtopic",
      "description": "What the learner should understand in this lesson",
      "searchQuery": "Precise YouTube search query for this subtopic"
    }
  ]
}

Rules:
- Include 6 to 12 lessons, ordered from prerequisites to advanced practice.
- Every lesson must directly belong to the requested subject.
- Do not add motivational, career, or unrelated videos.
- Each searchQuery must describe only its lesson.
- Do not return markdown or explanations.

Do not return markdown.
Do not return explanations.
`;

  try {
    const response = await llm.invoke([
      new SystemMessage('You are an adaptive curriculum planner.'),
      new HumanMessage(prompt)
    ]);

    let content = response.content;
    if (Array.isArray(content)) {
      content = content.map((item) => item.text || '').join('');
    }

    content = String(content)
      .replace(/```json/gi, '')
      .replace(/```/g, '')
      .trim();

    const roadmap = JSON.parse(content);
    return { recommendations: roadmap };
  } catch (error) {
    console.error('Recommendation generation error:', error.message);
    return {
      recommendations: {
        courseTitle: state.topic,
        lessons: [
          {
            title: state.topic + ' fundamentals',
            description: 'Begin with the core concepts of ' + state.topic + '.',
            searchQuery: state.topic + ' fundamentals tutorial'
          }
        ]
      }
    };
  }
}


// ======================================================
// BUILD LANGGRAPH
// ======================================================

const workflow = new StateGraph(AgentState)
  .addNode('fetchHistory', fetchHistoryNode)
  .addNode('decisionEngine', decisionNode)
  .addEdge(START, 'fetchHistory')
  .addEdge('fetchHistory', 'decisionEngine')
  .addEdge('decisionEngine', END);

const agentApp = workflow.compile();


// ======================================================
// 4. YOUTUBE SEARCH API
// ======================================================

app.get('/api/youtube/search', async (req, res) => {
  try {
    const query = req.query.q || 'JavaScript tutorials';
    const lessonTopic = String(req.query.lessonTopic || '').trim();

    if (!process.env.YOUTUBE_API_KEY) {
      return res.status(500).json({ error: 'YOUTUBE_API_KEY is missing from .env' });
    }

    const url = 'https://www.googleapis.com/youtube/v3/search';

    const response = await axios.get(url, {
      params: {
        part: 'snippet',
        maxResults: 5,
        q: query,
        type: 'video',
        videoDuration: 'medium',
        videoEmbeddable: 'true',
        safeSearch: 'strict',
        key: process.env.YOUTUBE_API_KEY
      }
    });

    const items = response.data.items || [];

    const videos = items
      .filter((item) => item.id && item.id.videoId)
      .map((item) => ({
        videoId: item.id.videoId,
        title: item.snippet.title,
        thumbnail:
          item.snippet.thumbnails?.medium?.url ||
          item.snippet.thumbnails?.default?.url ||
          '',
        channelTitle: item.snippet.channelTitle
      }))
      .filter((video) => !lessonTopic || isVideoRelevant(video, lessonTopic));

    res.json(videos);
  } catch (error) {
    console.error('YouTube Search Error:', error.response?.data || error.message);
    res.status(500).json({
      error: error.response?.data?.error?.message || error.message
    });
  }
});

function isVideoRelevant(video, lessonTopic) {
  const stopWords = new Set(['the', 'and', 'for', 'with', 'from', 'into', 'about', 'learn', 'tutorial', 'course']);
  const topicWords = lessonTopic.toLowerCase().match(/[a-z0-9]+/g) || [];
  const titleWords = video.title.toLowerCase().match(/[a-z0-9]+/g) || [];
  const meaningfulTopicWords = topicWords.filter((word) => word.length > 2 && !stopWords.has(word));
  if (!meaningfulTopicWords.length) return true;
  const matches = meaningfulTopicWords.filter((word) => titleWords.includes(word)).length;
  return matches / meaningfulTopicWords.length >= 0.5;
}

function isQuizRelatedToCourse(quizTopic, courseTopic) {
  const stopWords = new Set(['the', 'and', 'for', 'with', 'from', 'course', 'lesson']);
  const courseWords = String(courseTopic || '').toLowerCase().match(/[a-z0-9]+/g) || [];
  const quizWords = String(quizTopic || '').toLowerCase().match(/[a-z0-9]+/g) || [];
  const meaningfulCourseWords = courseWords.filter((word) => word.length > 2 && !stopWords.has(word));
  const meaningfulQuizWords = quizWords.filter((word) => word.length > 2 && !stopWords.has(word));
  if (!meaningfulCourseWords.length || !meaningfulQuizWords.length) return true;
  return meaningfulQuizWords.some((word) => meaningfulCourseWords.includes(word));
}


// ======================================================
// 5. SYNC VIDEO PROGRESS  (uses `returnDocument: 'after'`
//    so the response always reflects the just-saved data,
//    and every write is logged so you can see it land in
//    Mongo in real time)
// ======================================================

app.post('/api/progress/sync', async (req, res) => {
  try {
    const { userId, videoId, title, duration, courseId, courseTopic, lessonTitle, lessonIndex, learningMode } = req.body;
    const currentTime = req.body.currentTime;

    if (!videoId) {
      return res.status(400).json({ error: 'videoId is required' });
    }

    if (learningMode !== 'course') {
      return res.json({ success: true, tracking: false, reason: 'One-topic learning is not tracked.' });
    }

    if (!courseId || !courseTopic || !lessonTitle) {
      return res.status(400).json({
        error: 'Course, topic, and lesson title are required for progress tracking'
      });
    }

    const activeUserId = userId || 'user_default';

    const course = await LearningHistory.findOne({
      userId: activeUserId,
      courseId,
      topic: courseTopic,
      learningMode: 'course',
      courseStatus: 'active',
      'curriculum.title': lessonTitle
    });

    if (!course) {
      return res.status(400).json({ error: 'Progress must belong to an active course lesson' });
    }

    const current = Number(currentTime) || 0;
    const total = Number(duration) || 0;
    const percentWatched = total > 0 ? Math.min(100, (current / total) * 100) : 0;
    const completed = total > 0 && current / total >= 0.9;

    // make sure a Student record exists for this userId (auto-create on first sync)
    await Student.findOneAndUpdate(
      { userId: activeUserId },
      { $setOnInsert: { userId: activeUserId } },
      { upsert: true }
    );

    const progress = await UserProgress.findOneAndUpdate(
      { userId: activeUserId, courseId, videoId },
      {
        $set: {
          title: title || '',
          courseId,
          courseTopic: courseTopic || '',
          lessonTitle: lessonTitle || '',
          lessonIndex: Number.isInteger(lessonIndex) ? lessonIndex : 0,
          currentTime: current,
          duration: total,
          percentWatched,
          completed,
          lastWatchedAt: new Date()
        }
      },
      {
        upsert: true,
        returnDocument: 'after',
        setDefaultsOnInsert: true
      }
    );

    console.log(
      `[progress] ${activeUserId} -> ${videoId} @ ${Math.floor(current)}s / ${Math.floor(total)}s (${Math.round(percentWatched)}%)${completed ? ' [COMPLETED]' : ''}`
    );

    // Save completed video to learning history
    if (completed) {
      await LearningHistory.findOneAndUpdate(
        { userId: activeUserId, courseId },
        {
          $setOnInsert: { userId: activeUserId },
          $addToSet: { completedVideos: videoId }
        },
        { upsert: true, returnDocument: 'after' }
      );

      if (courseTopic && lessonTitle) {
        await LearningHistory.findOneAndUpdate(
          { userId: activeUserId, courseId, topic: courseTopic },
          {
            $set: { 'curriculum.$[lesson].completed': true },
            $max: { currentLesson: Number.isInteger(lessonIndex) ? lessonIndex + 1 : 0 }
          },
          {
            arrayFilters: [{ 'lesson.title': lessonTitle }],
            returnDocument: 'after'
          }
        );

        const updatedCourse = await LearningHistory.findOne({ userId: activeUserId, courseId });
        if (updatedCourse?.curriculum?.length && updatedCourse.curriculum.every((lesson) => lesson.completed)) {
          await LearningHistory.updateOne(
            { userId: activeUserId, courseId },
            { $set: { courseStatus: 'completed' } }
          );
        }
      }
    }

    res.json({ success: true, progress });
  } catch (error) {
    console.error('Progress Sync Error:', error.message);
    res.status(500).json({ error: error.message });
  }
});


// ======================================================
// 6. RESUME VIDEO
// ======================================================

app.get('/api/progress/resume/:videoId', async (req, res) => {
  try {
    const activeUserId = req.query.userId || 'user_default';
    const courseId = req.query.courseId || '';

    const progress = await UserProgress.findOne({
      userId: activeUserId,
      courseId,
      videoId: req.params.videoId
    });

    res.json({
      currentTime: progress ? progress.currentTime : 0,
      duration: progress ? progress.duration : 0,
      completed: progress ? progress.completed : false
    });
  } catch (error) {
    console.error('Resume Error:', error.message);
    res.status(500).json({ error: error.message });
  }
});


// ======================================================
// 6b. FULL PROGRESS LIST FOR A STUDENT (new)
//     GET /api/progress/:userId  -> every video this
//     student has ever watched, most recent first
// ======================================================

app.get('/api/progress/:userId', async (req, res) => {
  try {
    const progress = await UserProgress.find({ userId: req.params.userId }).sort({
      lastWatchedAt: -1
    });
    res.json(progress);
  } catch (error) {
    console.error('Progress List Error:', error.message);
    res.status(500).json({ error: error.message });
  }
});


// ======================================================
// 7. AI RECOMMENDATION ENDPOINT
// ======================================================

app.post('/api/agent/recommend', async (req, res) => {
  try {
    const { topic, userId } = req.body;

    if (!topic || !topic.trim()) {
      return res.status(400).json({ error: 'Topic is required' });
    }

    const activeUserId = userId || 'user_default';

    // auto-create Student record so every learner is tracked from their first request
    await Student.findOneAndUpdate(
      { userId: activeUserId },
      { $setOnInsert: { userId: activeUserId } },
      { upsert: true }
    );

    const result = await agentApp.invoke({
      userId: activeUserId,
      userIntent: 'RECOMMEND',
      topic: topic.trim()
    });

    const roadmap = result.recommendations || {};
    const lessons = Array.isArray(roadmap.lessons)
      ? roadmap.lessons
          .filter((lesson) => lesson && lesson.title && lesson.searchQuery)
          .map((lesson, index) => ({
            title: String(lesson.title),
            description: String(lesson.description || ''),
            order: index,
            completed: false,
            searchQuery: String(lesson.searchQuery)
          }))
      : [];

    if (!lessons.length) {
      return res.status(502).json({ error: 'The agent did not return a valid course roadmap.' });
    }

    const course = await LearningHistory.create({
      userId: activeUserId,
      courseId: crypto.randomUUID(),
      topic: topic.trim(),
      learningMode: 'course',
      courseStatus: 'active',
      curriculum: lessons,
      currentLesson: 0
    });

    res.json({
      courseTitle: roadmap.courseTitle || topic.trim(),
      learningMode: 'course',
      courseId: course.courseId,
      lessons
    });
  } catch (error) {
    console.error('Recommendation API Error:', error.message);
    res.status(500).json({ error: error.message });
  }
});


// ======================================================
// 8. GENERATE QUIZ
// ======================================================

app.post('/api/agent/quiz', async (req, res) => {
  try {
    const { topic, userId } = req.body;

    if (!topic) {
      return res.status(400).json({ error: 'Topic is required' });
    }

    const result = await agentApp.invoke({
      userId: userId || 'user_default',
      userIntent: 'GENERATE_QUIZ',
      topic
    });

    res.json(result.quiz);
  } catch (error) {
    console.error('Quiz API Error:', error.message);
    res.status(500).json({ error: error.message });
  }
});


// ======================================================
// 9. SUBMIT QUIZ
// ======================================================

app.post('/api/quiz/submit', async (req, res) => {
  try {
    const { userId, topic, courseId, videoId, answers, questions } = req.body;
    const activeUserId = userId || 'user_default';

    if (!Array.isArray(answers) || !Array.isArray(questions)) {
      return res.status(400).json({ error: 'Invalid quiz data' });
    }

    const courseProgress = await UserProgress.findOne({
      userId: activeUserId,
      courseId,
      videoId,
      courseTopic: { $ne: '' },
      lessonTitle: { $ne: '' }
    });
    if (!courseProgress) {
      return res.status(400).json({ error: 'Quiz rewards are only available for tracked course lessons.' });
    }

    let score = 0;
    questions.forEach((question, index) => {
      const userAnswer = answers[index];
      if (userAnswer && userAnswer === question.answer) {
        score++;
      }
    });

    await LearningHistory.findOneAndUpdate(
          { userId: activeUserId, courseId },
      {
        $setOnInsert: { userId: activeUserId },
        $push: {
          quizScores: {
            topic: topic || 'Unknown',
            videoId: videoId || '',
            score,
            total: questions.length,
            questions,
            answers,
            date: new Date()
          }
        }
      },
      { upsert: true, returnDocument: 'after' }
    );

    res.json({ success: true, score, total: questions.length });
  } catch (error) {
    console.error('Quiz Submission Error:', error.message);
    res.status(500).json({ error: error.message });
  }
});


// ======================================================
// 10. STUDENT DASHBOARD (per-student progress tracker)
// ======================================================

app.get('/api/student/:userId/dashboard', async (req, res) => {
  try {
    const { userId } = req.params;

    const watchedVideos = await UserProgress.find({ userId }).sort({ lastWatchedAt: -1 });
    const completedCount = watchedVideos.filter((video) => video.completed).length;
    const totalTimeSpentSeconds = watchedVideos.reduce(
      (total, video) => total + (video.currentTime || 0),
      0
    );

    const courses = await LearningHistory.find({ userId }).sort({ updatedAt: -1 });
    const selectedCourseId = req.query.courseId || courses[0]?.courseId;
    const learningHistory = courses.find((course) => course.courseId === selectedCourseId) || courses[0];
    const courseSummaries = courses.map((course) => {
      const completedLessons = course.curriculum.filter((lesson) => lesson.completed).length;
      const courseVideoIds = new Set(
        watchedVideos
          .filter((video) => video.courseId === course.courseId)
          .map((video) => video.videoId)
      );
      const courseQuizScores = course.quizScores.filter(
        (quiz) => courseVideoIds.has(quiz.videoId) && isQuizRelatedToCourse(quiz.topic, course.topic)
      );
      return {
        courseId: course.courseId,
        topic: course.topic,
        status: course.courseStatus,
        progress: course.curriculum.length
          ? Math.round((completedLessons / course.curriculum.length) * 100)
          : 0,
        completedLessons,
        totalLessons: course.curriculum.length,
        curriculum: course.curriculum,
        quizScores: courseQuizScores,
        updatedAt: course.updatedAt
      };
    });
    const selectedCourseVideoIds = new Set(
      watchedVideos
        .filter((video) => video.courseId === learningHistory?.courseId)
        .map((video) => video.videoId)
    );
    const quizScores = (learningHistory?.quizScores || []).filter(
      (quiz) => selectedCourseVideoIds.has(quiz.videoId) && isQuizRelatedToCourse(quiz.topic, learningHistory?.topic)
    );
    const curriculum = learningHistory?.curriculum || [];
    const completedLessons = curriculum.filter((lesson) => lesson.completed).length;
    const courseProgress = curriculum.length
      ? Math.round((completedLessons / curriculum.length) * 100)
      : 0;

    const averageProgress = watchedVideos.length
      ? Math.round(
          watchedVideos.reduce(
            (total, video) => total + (video.completed ? 100 : video.percentWatched || 0),
            0
          ) /
            watchedVideos.length
        )
      : 0;

    res.json({
      userId,
      courses: courseSummaries,
      selectedCourseId: learningHistory?.courseId || '',
      totalVideosAttempted: watchedVideos.length,
      completedVideos: completedCount,
      totalWatchTimeMinutes: Math.floor(totalTimeSpentSeconds / 60),
      averageProgress,
      lastActiveAt: watchedVideos[0]?.lastWatchedAt || null,
      currentTopic: learningHistory?.topic || '',
      learningMode: learningHistory?.learningMode || 'topic',
      courseStatus: learningHistory?.courseStatus || 'topic',
      courseProgress,
      currentLesson: learningHistory?.currentLesson || 0,
      curriculum,
      quizScores,
      history: watchedVideos
    });
  } catch (error) {
    console.error('Dashboard Error:', error.message);
    res.status(500).json({ error: error.message });
  }
});


// ======================================================
// 11. ADMIN ANALYTICS (progress across ALL students)
// ======================================================

app.get('/api/admin/analytics', async (req, res) => {
  try {
    const analytics = await UserProgress.aggregate([
      {
        $group: {
          _id: '$userId',
          totalVideosWatched: { $sum: 1 },
          completedLessons: { $sum: { $cond: ['$completed', 1, 0] } },
          totalWatchTime: { $sum: '$currentTime' },
          lastActive: { $max: '$lastWatchedAt' }
        }
      },
      { $sort: { lastActive: -1 } }
    ]);

    res.json(analytics);
  } catch (error) {
    console.error('Analytics Error:', error.message);
    res.status(500).json({ error: error.message });
  }
});


// ======================================================
// 12. HEALTH CHECK (new: quick way to verify DB status)
// ======================================================

app.get('/api/health', (req, res) => {
  const states = ['disconnected', 'connected', 'connecting', 'disconnecting'];
  res.json({
    ok: true,
    dbState: states[mongoose.connection.readyState] || 'unknown'
  });
});


// ======================================================
// 13. FRONTEND
// ======================================================

app.get('/', (req, res) => {
  res.send(`
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI YouTube Learning Platform</title>
<script src="https://www.youtube.com/iframe_api"></script>
<style>
:root { --ink: #172033; --muted: #667085; --line: #e6e8ee; --paper: #fff; --accent: #e85d3f; --accent-dark: #b83f2a; --soft: #fff4ef; }
* { box-sizing: border-box; }
body { font-family: Georgia, 'Times New Roman', serif; background: radial-gradient(circle at top right, #fff4df 0, transparent 34%), #f6f3ee; color: var(--ink); margin: 0; padding: 28px; }
.shell { max-width: 1380px; margin: 0 auto; }
.topbar { display: flex; justify-content: space-between; align-items: end; gap: 20px; margin-bottom: 24px; }
.view { display: none; }
.view.active { display: block; }
h1 { font-size: clamp(2rem, 4vw, 4rem); line-height: .95; margin: 0 0 8px; letter-spacing: 0; }
.eyebrow { color: var(--accent); font: 700 12px Arial, sans-serif; letter-spacing: 1.5px; text-transform: uppercase; }
.subtitle { color: var(--muted); margin: 0; font: 15px Arial, sans-serif; }
.user-select { display: flex; align-items: center; gap: 8px; font: 13px Arial, sans-serif; }
input, button { border: 1px solid var(--line); border-radius: 6px; padding: 12px 14px; font: inherit; }
input { background: var(--paper); color: var(--ink); }
input[type="text"] { width: min(70%, 560px); }
button { background: var(--accent); border-color: var(--accent); color: white; cursor: pointer; font: 700 13px Arial, sans-serif; }
button:hover { background: var(--accent-dark); }
.button-secondary { background: transparent; color: var(--accent-dark); }
.button-secondary:hover { color: white; }
.start-page { max-width: 980px; margin: 8vh auto 0; }
.start-page h2 { max-width: 620px; font-size: clamp(2rem, 5vw, 4rem); line-height: 1; margin-bottom: 12px; }
.start-page .intro { max-width: 560px; color: var(--muted); font: 16px/1.6 Arial, sans-serif; margin-bottom: 30px; }
.choice-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.choice { text-align: left; background: var(--paper); color: var(--ink); border: 1px solid var(--line); border-top: 5px solid var(--accent); border-radius: 10px; padding: 22px; box-shadow: 0 12px 30px rgba(23, 32, 51, .07); }
.choice:hover { background: #fffaf7; color: var(--ink); transform: translateY(-2px); }
.choice h3 { margin: 0 0 8px; font-size: 22px; }
.choice p { color: var(--muted); font: 14px/1.5 Arial, sans-serif; margin: 0 0 18px; }
.choice .choice-action { color: var(--accent-dark); font: 700 13px Arial, sans-serif; }
.workspace-label { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 14px; }
.workspace-label h2 { margin: 0; }
.workspace-label span { color: var(--muted); font: 12px Arial, sans-serif; }
.workspace-label span::before { content: '●'; color: var(--accent); margin-right: 6px; }
.container { display: grid; grid-template-columns: minmax(0, 1.7fr) minmax(320px, 1fr); gap: 22px; }
.main, .sidebar { min-width: 0; }
.panel { background: var(--paper); border: 1px solid var(--line); border-radius: 10px; padding: 18px; box-shadow: 0 8px 30px rgba(23, 32, 51, .06); }
.search-panel { margin-bottom: 16px; }
.search-panel label { display: block; color: var(--muted); font: 12px 700 Arial, sans-serif; letter-spacing: .8px; text-transform: uppercase; margin-bottom: 8px; }
.search-panel .search-controls { display: flex; gap: 8px; align-items: center; }
.search-panel .search-controls input { flex: 1; min-width: 0; width: auto; }
#player { width: 100%; aspect-ratio: 16 / 9; border-radius: 10px; background: #111827; overflow: hidden; }
#videoTitle { font-size: 22px; margin: 16px 0; }
.status { margin: 0 0 16px; padding: 10px 12px; border-left: 3px solid var(--accent); color: var(--muted); background: var(--soft); font: 13px Arial, sans-serif; }
.sidebar { display: flex; flex-direction: column; gap: 16px; }
.sidebar .panel { padding: 16px; }
h2, h3 { margin-top: 0; }
h3 { font-size: 18px; }
.video-card, .recommendation { background: #fafafa; border: 1px solid var(--line); padding: 12px; margin: 8px 0; border-radius: 6px; cursor: pointer; font: 14px Arial, sans-serif; }
.video-card:hover, .recommendation:hover { border-color: var(--accent); background: var(--soft); }
.recommendation { cursor: pointer; }
.quiz-box { background: var(--soft); border: 1px solid #f4c7b9; padding: 18px; margin-top: 15px; border-radius: 8px; }
.quiz-question { margin-bottom: 20px; font: 15px Arial, sans-serif; }
.dashboard-header { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.dashboard-header button { padding: 8px 11px; }
.metric-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; margin: 12px 0; }
.metric { background: #f7f8fa; border-radius: 6px; padding: 11px; }
.metric strong { display: block; font-size: 24px; color: var(--accent-dark); }
.metric span, .dashboard-note { color: var(--muted); font: 12px Arial, sans-serif; }
.progress-row { border-top: 1px solid var(--line); padding: 12px 0; font: 13px Arial, sans-serif; }
.progress-title { display: flex; justify-content: space-between; gap: 8px; font-weight: 700; }
.progress-bar { height: 6px; background: #e9eaee; border-radius: 6px; margin-top: 8px; overflow: hidden; }
.progress-fill { height: 100%; background: var(--accent); }
.dashboard-page { max-width: 900px; margin: 0 auto; }
.dashboard-page .panel { padding: 28px; }
.dashboard-page .dashboard-header { margin-bottom: 20px; }
.dashboard-page .dashboard-header h2 { margin: 0; }
.dashboard-page .progress-row { padding: 16px 0; }
.dashboard-hero { display: grid; grid-template-columns: 1fr 190px; gap: 24px; align-items: center; background: #172033; color: white; border-radius: 10px; padding: 24px; margin-bottom: 18px; }
.dashboard-hero h3 { margin: 5px 0 8px; font-size: 27px; }
.dashboard-hero .dashboard-note { color: #c8d0de; }
.dashboard-hero .eyebrow { color: #ffb39f; }
.course-ring { width: 150px; height: 150px; border-radius: 50%; display: grid; place-items: center; background: conic-gradient(var(--accent) var(--progress), #354158 0); position: relative; margin: auto; }
.course-ring::after { content: ''; width: 112px; height: 112px; border-radius: 50%; background: #172033; position: absolute; }
.course-ring strong, .course-ring span { position: relative; z-index: 1; }
.course-ring strong { font-size: 28px; }
.course-ring span { display: block; color: #c8d0de; font: 11px Arial, sans-serif; text-align: center; }
.ring-label { display: flex; flex-direction: column; align-items: center; }
.dashboard-columns { display: grid; grid-template-columns: 1.1fr .9fr; gap: 18px; }
.course-list { display: flex; gap: 10px; overflow-x: auto; padding: 2px 0 18px; }
.course-card { min-width: 190px; flex: 1; background: #fffaf7; color: var(--ink); border: 1px solid var(--line); border-left: 4px solid var(--accent); border-radius: 7px; padding: 14px; text-align: left; }
.course-card:hover { background: var(--soft); color: var(--ink); }
.course-card.selected { box-shadow: 0 0 0 2px var(--accent); }
.course-card strong, .course-card span { pointer-events: none; }
.course-card strong { display: block; margin-bottom: 10px; }
.course-card .progress-bar { margin: 8px 0 5px; }
.review-list { display: grid; gap: 10px; }
.review-item { border: 1px solid var(--line); border-radius: 6px; padding: 12px; background: #fafafa; }
.review-item summary { cursor: pointer; font: 700 13px Arial, sans-serif; }
.review-question { border-top: 1px solid var(--line); margin-top: 10px; padding-top: 10px; font: 13px/1.45 Arial, sans-serif; }
.answer-correct { color: #2d7a4d; font-weight: 700; }
.answer-wrong { color: var(--accent-dark); font-weight: 700; }
.dashboard-section { background: #fff; border: 1px solid var(--line); border-radius: 10px; padding: 18px; }
.dashboard-section h3 { margin-bottom: 14px; }
.next-lesson { background: var(--soft); border-left: 4px solid var(--accent); padding: 14px; border-radius: 5px; }
.next-lesson strong { display: block; margin-bottom: 5px; }
.dashboard-section .metric-grid { grid-template-columns: repeat(2, 1fr); margin: 0; }
@media (max-width: 850px) { body { padding: 18px; } .topbar { display: block; } .user-select { margin-top: 18px; } .container { grid-template-columns: 1fr; } input[type="text"] { width: 65%; } }
@media (max-width: 650px) { .choice-grid, .dashboard-columns, .dashboard-hero { grid-template-columns: 1fr; } .start-page { margin-top: 4vh; } .course-ring { margin-top: 4px; } .search-controls { flex-wrap: wrap; } .search-controls button { width: 100%; } }
</style>
</head>
<body>
<div class="shell">
<div class="topbar">
<div><div class="eyebrow">Adaptive study studio</div><h1>Learn with momentum.</h1><p class="subtitle">Search a lesson, track your progress, and keep your next step visible.</p></div>

<div class="user-select">
<label for="studentId">Active Student ID:</label>
<input type="text" id="studentId" value="student_1" style="width:150px;">
<button type="button" id="homeButton" class="button-secondary">Home</button>
<button type="button" id="dashboardButton">Dashboard</button>
</div>

 </div>

<div id="startView" class="view active start-page">
<div class="eyebrow">Adaptive study studio</div>
<h2>What kind of learning do you need today?</h2>
<p class="intro">Choose a guided course when you want steady progress, or search for one topic when you only need a quick lesson.</p>
<div class="choice-grid">
<button type="button" id="courseChoice" class="choice">
<h3>Build a course</h3>
<p>Get an ordered roadmap, lesson-by-lesson tracking, resume support, quizzes, and a completion reward.</p>
<span class="choice-action">Plan a course →</span>
</button>
<button type="button" id="topicChoice" class="choice">
<h3>Learn one topic</h3>
<p>Find a focused video quickly. Your course dashboard stays unchanged and no reward is created.</p>
<span class="choice-action">Search a topic →</span>
</button>
</div>
</div>

<div id="learningView" class="view">
<div class="workspace-label"><div><div class="eyebrow">Learning workspace</div><h2 id="workspaceTitle">Choose a lesson</h2></div><span id="workspaceHint">Course progress is off</span></div>
<div class="container">
<div class="main">
<div class="panel search-panel">
<label for="topicInput">What do you want to learn?</label>
<div class="search-controls">
<input type="text" id="topicInput" placeholder="e.g. Node.js, data structures, photography">
<button id="primarySearchButton" onclick="searchOneTopic()">Find videos</button>
</div>
</div>

<div id="status" class="status">Ready</div>
<div id="player"></div>
<h3 id="videoTitle">Select a video to start</h3>
<div id="quizContainer"></div>
</div>

<div class="sidebar">
<div class="panel">
<h3 id="recommendationsHeading">Your course plan</h3>
<div id="recommendations">Run a search to get AI recommendations</div>
<h3 id="resultsHeading">Lesson videos</h3>
<div id="searchResults"></div>
</div>
</div>
</div>
</div>
</div>

<div id="dashboardView" class="view dashboard-page">
<div class="panel">
<div class="dashboard-header">
<div><div class="eyebrow">Your learning record</div><h2>Student dashboard</h2></div>
<button onclick="showLearning()">Back to learning</button>
</div>
<div id="dashboard"><div class="dashboard-note">Loading student progress...</div></div>
</div>
</div>

<script>
let player = null;
let currentVideoId = '';
let currentVideoTitle = '';
let syncInterval = null;
let currentQuiz = null;
let pendingVideo = null;
let currentCourseTopic = '';
let currentCourseId = '';
let currentLessonTitle = '';
let currentLessonIndex = 0;
let currentLearningMode = 'topic';

document.getElementById('homeButton').addEventListener('click', showStartPage);
document.getElementById('dashboardButton').addEventListener('click', showDashboard);
document.getElementById('courseChoice').addEventListener('click', beginCourse);
document.getElementById('topicChoice').addEventListener('click', beginOneTopic);
document.getElementById('dashboard').addEventListener('click', function (event) {
  const courseCard = event.target.closest('[data-course-id]');
  if (courseCard) selectCourse(courseCard.dataset.courseId);
});

function getActiveUserId() {
  return (document.getElementById('studentId').value.trim()) || 'user_default';
}

function setStatus(message) {
  document.getElementById('status').innerText = message;
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function onYouTubeIframeAPIReady() {
  console.log('YouTube API Ready');
  if (pendingVideo) {
    const video = pendingVideo;
    pendingVideo = null;
    loadVideo(video.videoId, video.title);
  }
}

async function loadVideo(videoId, title) {
  currentVideoId = videoId;
  currentVideoTitle = title;
  document.getElementById('videoTitle').innerText = title;

  if (!window.YT || !window.YT.Player) {
    pendingVideo = { videoId: videoId, title: title };
    setStatus('YouTube player is loading. Your video will open shortly.');
    return;
  }

  try {
    let startSeconds = 0;
    if (currentLearningMode === 'course') {
      const response = await fetch('/api/progress/resume/' + encodeURIComponent(videoId) + '?userId=' + encodeURIComponent(getActiveUserId()) + '&courseId=' + encodeURIComponent(currentCourseId));
      const data = await response.json();
      startSeconds = data.currentTime || 0;
    }

    if (player) {
      player.loadVideoById({ videoId: videoId, startSeconds: Math.floor(startSeconds) });
    } else {
      player = new YT.Player('player', {
        videoId: videoId,
        playerVars: { start: Math.floor(startSeconds) },
        events: { onStateChange: onPlayerStateChange }
      });
    }

    setStatus('Video loaded. Resuming from ' + Math.floor(startSeconds) + ' seconds.');
  } catch (error) {
    console.error(error);
    setStatus('Failed to load video progress.');
  }
}

function onPlayerStateChange(event) {
  if (event.data === YT.PlayerState.PLAYING) {
    startProgressTracking();
  } else {
    stopProgressTracking();
  }

  if (event.data === YT.PlayerState.ENDED) {
    stopProgressTracking();
    if (currentLearningMode === 'course') {
      saveFinalProgress();
      triggerQuiz();
    } else {
      setStatus('Topic complete. No course progress or reward was recorded.');
    }
  }
}

function startProgressTracking() {
  if (syncInterval) clearInterval(syncInterval);
  syncInterval = setInterval(syncProgress, 5000);
}

function stopProgressTracking() {
  if (syncInterval) {
    clearInterval(syncInterval);
    syncInterval = null;
  }
}

async function syncProgress() {
  if (!player || !player.getCurrentTime || !currentVideoId) return;

  const currentTime = player.getCurrentTime();
  const duration = player.getDuration();

  try {
    const response = await fetch('/api/progress/sync', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        userId: getActiveUserId(),
        videoId: currentVideoId,
        title: currentVideoTitle,
        learningMode: currentLearningMode,
        courseId: currentCourseId,
        courseTopic: currentCourseTopic,
        lessonTitle: currentLessonTitle,
        lessonIndex: currentLessonIndex,
        currentTime: currentTime,
        duration: duration
      })
    });

    if (response.ok && document.getElementById('dashboardView').classList.contains('active')) {
      loadDashboard();
    }
  } catch (error) {
    console.error('Progress sync error:', error);
  }
}

async function saveFinalProgress() {
  if (!player || !currentVideoId) return;

  const currentTime = player.getCurrentTime();
  const duration = player.getDuration();

  try {
    const response = await fetch('/api/progress/sync', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        userId: getActiveUserId(),
        videoId: currentVideoId,
        title: currentVideoTitle,
        learningMode: currentLearningMode,
        courseId: currentCourseId,
        courseTopic: currentCourseTopic,
        lessonTitle: currentLessonTitle,
        lessonIndex: currentLessonIndex,
        currentTime: duration,
        duration: duration
      })
    });

    if (response.ok) {
      loadDashboard();
    }
  } catch (error) {
    console.error(error);
  }
}

async function searchAndRecommend() {
  const topic = document.getElementById('topicInput').value.trim();
  if (!topic) { alert('Please enter a topic.'); return; }

  setStatus('AI is creating your learning path...');

  try {
    currentLearningMode = 'course';
    document.getElementById('workspaceTitle').innerText = 'Building your course';
    document.getElementById('workspaceHint').innerText = 'Course progress is on';
    document.getElementById('recommendationsHeading').innerText = 'Your course plan';
    document.getElementById('resultsHeading').innerText = 'Lesson videos';
    document.getElementById('learningView').classList.add('active');
    document.getElementById('startView').classList.remove('active');
    const agentResponse = await fetch('/api/agent/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic: topic, userId: getActiveUserId() })
    });

    const agentData = await agentResponse.json();
    if (!agentResponse.ok) throw new Error(agentData.error || 'AI recommendation failed.');

    const lessons = Array.isArray(agentData.lessons) ? agentData.lessons : [];
    currentCourseTopic = topic;
    currentCourseId = agentData.courseId || '';
    const recDiv = document.getElementById('recommendations');
    recDiv.innerHTML = '';

    lessons.forEach(function (lesson, lessonIndex) {
      const div = document.createElement('div');
      div.className = 'recommendation';
      div.innerHTML = '<strong>' + (lessonIndex + 1) + '. ' + escapeHtml(lesson.title) + '</strong>' +
        '<br><small>' + escapeHtml(lesson.description) + '</small>';
      div.setAttribute('role', 'button');
      div.setAttribute('tabindex', '0');
      div.addEventListener('click', function () {
        loadLesson(lesson, lessonIndex);
      });
      div.addEventListener('keydown', function (event) {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          div.click();
        }
      });
      recDiv.appendChild(div);
    });

    if (!lessons.length) {
      throw new Error('The agent did not return any course lessons.');
    }

    loadLesson(lessons[0], 0);
  } catch (error) {
    console.error(error);
    setStatus('Error: ' + error.message);
  }
}

async function searchOneTopic() {
  const topic = document.getElementById('topicInput').value.trim();
  if (!topic) { alert('Please enter a topic.'); return; }

  currentLearningMode = 'topic';
  currentCourseId = '';
  document.getElementById('workspaceTitle').innerText = 'One-topic search';
  document.getElementById('workspaceHint').innerText = 'Course progress is off';
  document.getElementById('recommendationsHeading').innerText = 'About this search';
  document.getElementById('resultsHeading').innerText = 'Topic videos';
  document.getElementById('learningView').classList.add('active');
  document.getElementById('startView').classList.remove('active');
  currentCourseTopic = '';
  currentLessonTitle = '';
  currentLessonIndex = 0;
  document.getElementById('recommendations').innerHTML = '<div class="dashboard-note">One-topic learning is not added to your course progress.</div>';
  setStatus('Finding videos for this topic...');

  try {
    const response = await fetch('/api/youtube/search?q=' + encodeURIComponent(topic));
    const videos = await response.json();
    if (!response.ok) throw new Error(videos.error || 'YouTube search failed.');
    renderSearchResults(videos);
    setStatus('Topic videos ready. Course tracking is off for this session.');
  } catch (error) {
    console.error(error);
    setStatus('Error: ' + error.message);
  }
}

async function loadLesson(lesson, lessonIndex) {
    currentCourseTopic = document.getElementById('topicInput').value.trim();
    currentLessonTitle = lesson.title;
    currentLessonIndex = lessonIndex;
    setStatus('Searching videos for lesson ' + (lessonIndex + 1) + ': ' + lesson.title);

  try {
    const query = lesson.searchQuery || lesson.title;
    const ytResponse = await fetch('/api/youtube/search?q=' + encodeURIComponent(query) + '&lessonTopic=' + encodeURIComponent(lesson.title));
    const videos = await ytResponse.json();
    if (!ytResponse.ok) throw new Error(videos.error || 'YouTube search failed.');

    renderSearchResults(videos);
    setStatus('Videos ready for lesson ' + (lessonIndex + 1) + '. Choose one to study.');
  } catch (error) {
    console.error(error);
    setStatus('Error: ' + error.message);
  }
}

function renderSearchResults(videos) {
    const searchDiv = document.getElementById('searchResults');
    searchDiv.innerHTML = '';

    videos.forEach(function (video) {
      const card = document.createElement('div');
      card.className = 'video-card';

      const strong = document.createElement('strong');
      strong.innerText = video.title;

      const br = document.createElement('br');

      const small = document.createElement('small');
      small.innerText = video.channelTitle;

      card.appendChild(strong);
      card.appendChild(br);
      card.appendChild(small);

      card.addEventListener('click', function () {
        loadVideo(video.videoId, video.title);
      });

      searchDiv.appendChild(card);
    });
}

async function triggerQuiz() {
  if (currentLearningMode !== 'course') return;
  const topic = document.getElementById('topicInput').value.trim() || 'Lesson';
  setStatus('Video completed! Generating AI quiz...');

  try {
    const response = await fetch('/api/agent/quiz', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic: topic, userId: getActiveUserId() })
    });

    const quiz = await response.json();
    if (!response.ok) throw new Error(quiz.error || 'Quiz generation failed.');
    if (!quiz.questions || !Array.isArray(quiz.questions)) throw new Error('Invalid quiz received.');

    currentQuiz = quiz;
    renderQuiz(quiz);
    setStatus('Quiz generated. Answer all questions.');
  } catch (error) {
    console.error('Quiz error:', error);
    setStatus('Quiz error: ' + error.message);
  }
}

function renderQuiz(quiz) {
  const container = document.getElementById('quizContainer');
  container.innerHTML = '';

  const box = document.createElement('div');
  box.className = 'quiz-box';

  const heading = document.createElement('h3');
  heading.innerText = 'Lesson Completed! AI Quiz';
  box.appendChild(heading);

  quiz.questions.forEach(function (question, questionIndex) {
    const questionDiv = document.createElement('div');
    questionDiv.className = 'quiz-question';

    const questionText = document.createElement('p');
    questionText.innerHTML = '<strong>Q' + (questionIndex + 1) + ': ' + question.question + '</strong>';
    questionDiv.appendChild(questionText);

    question.options.forEach(function (option, optionIndex) {
      const label = document.createElement('label');
      const radio = document.createElement('input');
      radio.type = 'radio';
      radio.name = 'question-' + questionIndex;
      radio.value = option;

      label.appendChild(radio);
      label.appendChild(document.createTextNode(' ' + option));

      questionDiv.appendChild(label);
      questionDiv.appendChild(document.createElement('br'));
    });

    box.appendChild(questionDiv);
  });

  const submitButton = document.createElement('button');
  submitButton.innerText = 'Submit Quiz';
  submitButton.addEventListener('click', submitQuiz);
  box.appendChild(submitButton);

  container.appendChild(box);
}

async function submitQuiz() {
  if (!currentQuiz) return;

  const answers = [];
  for (let i = 0; i < currentQuiz.questions.length; i++) {
    const selected = document.querySelector('input[name="question-' + i + '"]:checked');
    if (!selected) { alert('Please answer question ' + (i + 1)); return; }
    answers.push(selected.value);
  }

  
  try {
    const response = await fetch('/api/quiz/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        userId: getActiveUserId(),
        topic: document.getElementById('topicInput').value,
        courseId: currentCourseId,
        videoId: currentVideoId,
        answers: answers,
        questions: currentQuiz.questions
      })
    });

    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Quiz submission failed.');

    const percentage = Math.round((result.score / result.total) * 100);

    document.getElementById('quizContainer').innerHTML =
      '<div class="quiz-box"><h3>Quiz Result</h3><p>You scored <strong>' +
      result.score + '/' + result.total + '</strong></p><p>Score: ' + percentage + '%</p></div>';

    setStatus('Quiz submitted successfully.');
  } catch (error) {
    console.error(error);
    setStatus('Quiz submission error: ' + error.message);
  }
}

async function loadDashboard(courseId) {
  try {
    const userId = getActiveUserId();
    const query = courseId ? '?courseId=' + encodeURIComponent(courseId) : '';
    const response = await fetch('/api/student/' + encodeURIComponent(userId) + '/dashboard' + query);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Dashboard failed.');

    const dashboard = document.getElementById('dashboard');
    const history = Array.isArray(data.history) ? data.history : [];
    const progressRows = history.length
      ? history.slice(0, 5).map(function (video) {
          const watched = video.completed
            ? 100
            : Math.round(video.percentWatched || 0);
          const title = escapeHtml(video.title || video.videoId);
          return '<div class="progress-row">' +
            '<div class="progress-title"><span>' + title + '</span><span>' + watched + '%</span></div>' +
            '<div class="progress-bar"><div class="progress-fill" style="width:' + watched + '%"></div></div>' +
            '<div class="dashboard-note">' + (video.completed ? 'Completed lesson' : 'In progress') + '</div>' +
          '</div>';
        }).join('')
      : '<div class="dashboard-note">No videos watched yet. Start a lesson to see progress here.</div>';
    const curriculumRows = Array.isArray(data.curriculum) && data.curriculum.length
      ? data.curriculum.map(function (lesson, lessonIndex) {
          const state = lesson.completed
            ? 'Completed'
            : lessonIndex === data.currentLesson
              ? 'Next lesson'
              : 'Upcoming';
          return '<div class="progress-row"><div class="progress-title"><span>' +
            (lessonIndex + 1) + '. ' + escapeHtml(lesson.title) + '</span><span>' + state + '</span></div>' +
            '<div class="dashboard-note">' + escapeHtml(lesson.description || '') + '</div></div>';
        }).join('')
      : '<div class="dashboard-note">Create a course to see its roadmap here.</div>';
    const nextLesson = Array.isArray(data.curriculum)
      ? data.curriculum.find((lesson) => !lesson.completed)
      : null;
    const courseTitle = escapeHtml(data.currentTopic || 'Your learning path');
    const courseStatus = escapeHtml(data.courseStatus === 'completed' ? 'Course complete' : data.learningMode === 'course' ? 'Active course' : 'No active course');
    const nextLessonMarkup = nextLesson
      ? '<div class="next-lesson"><strong>' + escapeHtml(nextLesson.title) + '</strong><span class="dashboard-note">' + escapeHtml(nextLesson.description || 'Continue with your next lesson.') + '</span></div>'
      : '<div class="next-lesson"><strong>Choose a learning path</strong><span class="dashboard-note">Start a course from Home to see your next lesson here.</span></div>';
    const courseCards = Array.isArray(data.courses) && data.courses.length
      ? data.courses.map(function (course) {
          const selected = course.courseId === data.selectedCourseId ? ' selected' : '';
          return '<button type="button" class="course-card' + selected + '" data-course-id="' + escapeHtml(course.courseId) + '"><strong>' + escapeHtml(course.topic) + '</strong><span class="dashboard-note">' + escapeHtml(course.status) + '</span><div class="progress-bar"><div class="progress-fill" style="width:' + course.progress + '%"></div></div><span class="dashboard-note">' + course.progress + '% complete · ' + course.completedLessons + '/' + course.totalLessons + ' lessons</span></button>';
        }).join('')
      : '<div class="dashboard-note">No courses yet. Start one from Home.</div>';
    const quizReviews = Array.isArray(data.quizScores) && data.quizScores.length
      ? data.quizScores.slice().reverse().map(function (quiz) {
          const questions = Array.isArray(quiz.questions) ? quiz.questions : [];
          const questionMarkup = questions.length
            ? questions.map(function (question, questionIndex) {
                const selected = quiz.answers?.[questionIndex] || 'Not answered';
                const correct = selected === question.answer;
                return '<div class="review-question"><strong>Q' + (questionIndex + 1) + ': ' + escapeHtml(question.question) + '</strong><div>Your answer: <span class="' + (correct ? 'answer-correct' : 'answer-wrong') + '">' + escapeHtml(selected) + '</span></div><div>Correct answer: <span class="answer-correct">' + escapeHtml(question.answer || '') + '</span></div></div>';
              }).join('')
            : '<div class="dashboard-note">This quiz was completed before answer review was enabled.</div>';
          return '<details class="review-item"><summary>' + escapeHtml(quiz.topic || 'Quiz') + ' · ' + quiz.score + '/' + quiz.total + '</summary>' + questionMarkup + '</details>';
        }).join('')
      : '<div class="dashboard-note">Complete a course quiz to review your answers here.</div>';

    dashboard.innerHTML =
      '<h3>Your courses</h3><div class="course-list">' + courseCards + '</div>' +
      '<div class="dashboard-hero">' +
        '<div><div class="eyebrow">' + courseStatus + '</div><h3>' + courseTitle + '</h3>' +
          '<div class="dashboard-note">Your learning path, next step, and recent activity in one place.</div></div>' +
        '<div class="course-ring" style="--progress:' + data.courseProgress + '%"><div class="ring-label"><strong>' + data.courseProgress + '%</strong><span>course progress</span></div></div>' +
      '</div>' +
      '<div class="dashboard-columns">' +
        '<section class="dashboard-section"><h3>Next lesson</h3>' + nextLessonMarkup + '<h3 style="margin-top:22px">Course roadmap</h3>' + curriculumRows + '</section>' +
        '<section class="dashboard-section"><h3>Your activity</h3><div class="metric-grid">' +
          '<div class="metric"><strong>' + data.completedVideos + '</strong><span>Completed</span></div>' +
          '<div class="metric"><strong>' + data.totalVideosAttempted + '</strong><span>Lessons started</span></div>' +
          '<div class="metric"><strong>' + data.averageProgress + '%</strong><span>Average watch</span></div>' +
          '<div class="metric"><strong>' + data.totalWatchTimeMinutes + 'm</strong><span>Watch time</span></div>' +
        '</div><h3 style="margin-top:22px">Recent videos</h3>' + progressRows + '</section>' +
      '</div><section class="dashboard-section" style="margin-top:18px"><h3>Review your answers</h3><div class="review-list">' + quizReviews + '</div></section>';
  } catch (error) {
    console.error(error);
    document.getElementById('dashboard').innerHTML =
      '<div class="dashboard-note">Dashboard unavailable: ' + error.message + '</div>';
  }
}

function showDashboard() {
  document.getElementById('startView').classList.remove('active');
  document.getElementById('learningView').classList.remove('active');
  document.getElementById('dashboardView').classList.add('active');
  loadDashboard();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function selectCourse(courseId) {
  loadDashboard(courseId);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function showLearning() {
  document.getElementById('startView').classList.remove('active');
  document.getElementById('dashboardView').classList.remove('active');
  document.getElementById('learningView').classList.add('active');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function showStartPage() {
  document.getElementById('learningView').classList.remove('active');
  document.getElementById('dashboardView').classList.remove('active');
  document.getElementById('startView').classList.add('active');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function beginCourse() {
  showLearning();
  currentLearningMode = 'course';
  document.getElementById('workspaceTitle').innerText = 'Build a course';
  document.getElementById('workspaceHint').innerText = 'Course progress is on';
  document.getElementById('primarySearchButton').innerText = 'Plan my course';
  document.getElementById('primarySearchButton').onclick = searchAndRecommend;
  document.getElementById('topicInput').focus();
}

function beginOneTopic() {
  showLearning();
  currentLearningMode = 'topic';
  document.getElementById('workspaceTitle').innerText = 'Learn one topic';
  document.getElementById('workspaceHint').innerText = 'Course progress is off';
  document.getElementById('primarySearchButton').innerText = 'Find videos';
  document.getElementById('primarySearchButton').onclick = searchOneTopic;
  document.getElementById('topicInput').focus();
}
</script>
</body>
</html>
`);
});


// ======================================================
// 14. START SERVER (fixed: now waits for MongoDB to be
//     connected before accepting requests)
// ======================================================

const PORT = process.env.PORT || 3000;

connectDB().then(() => {
  app.listen(PORT, () => {
    console.log(`Server running at http://localhost:${PORT}`);
  });
});
