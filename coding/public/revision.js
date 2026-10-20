/* Topic video retrieval. No model, student code, or personal profile is sent
   to YouTube. Cached records are video metadata, not offline video downloads. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.CodingRevision = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const TOPIC_QUERIES = Object.freeze({
    loops: 'Python for while loops range boundaries beginner worked examples',
    arrays: 'Python lists arrays traversal beginner DSA worked examples',
    strings: 'Python strings indexing manipulation beginner DSA examples',
    binary_search: 'binary search Python sorted array boundaries step by step',
    two_pointers: 'two pointers algorithm Python step by step worked examples',
    stacks: 'stack data structure Python push pop balanced parentheses examples',
    recursion: 'Python recursion base case recursive call step by step examples',
    dynamic_programming: 'dynamic programming Python states recurrence base cases beginner examples',
    sliding_window: 'sliding window algorithm Python step by step examples'
  });
  const inFlight = new Map(), failures = new Map();
  const CACHE_AGE = 6 * 60 * 60 * 1000, RETRY_DELAY = 60 * 1000;
  function cacheKey(topic) { return 'revision-videos:v1:' + topic; }
  async function cachedVideos(topic) {
    try { return await globalThis.PracticeDB.get(cacheKey(topic)); } catch (_) { return null; }
  }
  async function videosFor(topic, force = false) {
    const query = TOPIC_QUERIES[topic];
    if (!query) return { videos: [], error: 'Choose a specific topic to find revision videos.' };
    const cached = await cachedVideos(topic);
    if (!navigator.onLine) return { videos: cached?.videos || [], offline: true, cached: Boolean(cached) };
    if (!force && cached && Date.now() - cached.fetchedAt < CACHE_AGE) return { videos: cached.videos, cached: true };
    const failure = failures.get(topic);
    if (!force && failure && Date.now() - failure.at < RETRY_DELAY) return failure.result;
    if (inFlight.has(topic)) return inFlight.get(topic);
    const work = (async () => {
      try {
        const params = new URLSearchParams({ q: query, lessonTopic: topic.replace(/_/g, ' ') });
        const response = await fetch('/api/youtube/search?' + params, { signal: AbortSignal.timeout(20000) });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Video search is temporarily unavailable.');
        if (!Array.isArray(data)) throw new Error('Video search returned an unexpected response.');
        const seen = new Set();
        const videos = data.filter(v => v && /^[A-Za-z0-9_-]{11}$/.test(v.videoId) && typeof v.title === 'string' && !seen.has(v.videoId) && seen.add(v.videoId))
          .slice(0, 3).map(v => ({ videoId: v.videoId, title: v.title.slice(0, 200), channelTitle: String(v.channelTitle || '').slice(0, 150) }));
        try { await globalThis.PracticeDB.set(cacheKey(topic), { videos, fetchedAt: Date.now() }); } catch (_) {}
        failures.delete(topic);
        return { videos };
      } catch (error) {
        const result = { videos: cached?.videos || [], cached: Boolean(cached), error: error.name === 'TimeoutError' ? 'Video search timed out. Check your connection and retry.' : error.message };
        failures.set(topic, { at: Date.now(), result });
        return result;
      } finally { inFlight.delete(topic); }
    })();
    inFlight.set(topic, work);
    return work;
  }
  function learningURL(context, video) {
    const query = new URLSearchParams({ userId: context.userId, revisionTopic: context.topic, returnQuestion: context.questionId || '' });
    if (context.courseId) query.set('courseId', context.courseId);
    if (context.questionId?.startsWith('custom:')) query.set('returnSource', 'custom');
    if (video) { query.set('videoId', video.videoId); query.set('videoTitle', video.title); }
    return '/?' + query + '#topic';
  }
  function element(tag, text, className) {
    const el = document.createElement(tag);
    if (text !== undefined) el.textContent = text;
    if (className) el.className = className;
    return el;
  }
  function mount(container, options) {
    const topic = options.topic;
    if (!TOPIC_QUERIES[topic]) return;
    container.classList.add('revision-videos');
    container.dataset.videoTopic = topic;
    container.replaceChildren();
    container.append(element('h4', 'Videos to review this topic'));
    const message = element('p', 'Finding topic videos…', 'small'); message.setAttribute('role', 'status');
    const list = element('div', undefined, 'revision-video-list');
    const retry = element('button', 'Refresh videos', 'secondary'); retry.type = 'button';
    const search = element('a', 'Search YouTube', 'revision-search');
    search.href = 'https://www.youtube.com/results?' + new URLSearchParams({ search_query: TOPIC_QUERIES[topic] });
    search.target = '_blank'; search.rel = 'noopener noreferrer';
    const actions = element('div', undefined, 'actions'); actions.append(retry, search);
    container.append(message, list, actions);
    const offlineHint = 'Connect to the internet to watch videos. Your coding practice and local hints still work offline.';
    let generation = 0;
    async function load(force = false) {
      const request = ++generation;
      retry.disabled = true;
      const result = await videosFor(topic, force);
      if (!container.isConnected || request !== generation) return;
      list.replaceChildren();
      container.dataset.videoState = result.offline ? 'offline' : result.error ? 'error' : 'ready';
      message.textContent = result.offline ? offlineHint : result.error ? result.error + (result.videos.length ? ' Previously found videos are shown below.' : '') : result.videos.length ? 'Suggested from the topic of your coding attempts. Review a lesson, then test your code again.' : 'No matching videos were returned. Try refreshing or searching YouTube.';
      for (const video of result.videos) {
        const item = element('div', undefined, 'revision-video');
        item.append(element('strong', video.title), element('p', video.channelTitle, 'small'));
        const link = element('a', 'Watch lesson →', 'watch-revision');
        link.href = learningURL(options.getContext(), video);
        link.addEventListener('click', async event => {
          if (!navigator.onLine) { event.preventDefault(); return; }
          link.href = learningURL(options.getContext(), video);
          if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
          event.preventDefault();
          if (await options.beforeNavigate() !== false) location.href = link.href;
        });
        // Offline metadata remains readable; navigation is enabled on reconnect.
        if (!navigator.onLine) { link.removeAttribute('href'); link.setAttribute('aria-disabled', 'true'); }
        item.append(link); list.append(item);
      }
      retry.disabled = !navigator.onLine;
      if (!navigator.onLine) { search.removeAttribute('href'); search.setAttribute('aria-disabled', 'true'); }
      else { search.href = 'https://www.youtube.com/results?' + new URLSearchParams({ search_query: TOPIC_QUERIES[topic] }); search.removeAttribute('aria-disabled'); }
    }
    retry.addEventListener('click', () => { void load(true); });
    void load();
  }
  return { TOPIC_QUERIES, learningURL, mount };
});
