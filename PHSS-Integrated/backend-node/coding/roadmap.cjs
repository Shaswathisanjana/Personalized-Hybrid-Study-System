'use strict';

// These rules connect evidence to a course; they do not diagnose a misconception.
const topicWords = {
  loops: /\b(loop|loops|iteration|iterations)\b/,
  arrays: /\b(array|arrays|lists)\b/,
  strings: /\b(string|strings)\b/,
  binary_search: /\bbinary search\b/,
  two_pointers: /\btwo pointers?\b/,
  stacks: /\bstacks?\b/,
  recursion: /\b(recursion|recursive)\b/,
  dynamic_programming: /\bdynamic programming\b/,
  sliding_window: /\bsliding windows?\b/
};

function matchesCourse(task, course) {
  if (!course) return true;
  const linked = Array.isArray(task.courseIds) ? task.courseIds : [];
  if (linked.length) return linked.includes(course.courseId);
  const text = [course.topic, ...(course.curriculum || []).flatMap(lesson =>
    [lesson.title, lesson.description, lesson.searchQuery])].join(' ').toLowerCase().replace(/[_-]+/g, ' ');
  return Boolean(topicWords[task.topic]?.test(text)) ||
    /\b(python|programming|coding|dsa|computer science|data structures?|algorithms?)\b/.test(text);
}

function tasksForCourse(tasks = [], course) {
  return tasks.filter(task => matchesCourse(task, course));
}

function buildLearningPath(course, tasks = []) {
  const lessons = (course?.curriculum || []).map((lesson, lessonIndex) => ({
    kind: 'lesson', id: `lesson:${course.courseId}:${lessonIndex}`, lessonIndex,
    title: lesson.title, description: lesson.description || '',
    searchQuery: lesson.searchQuery || lesson.title, completed: Boolean(lesson.completed)
  }));
  const revisions = tasksForCourse(tasks, course).filter(task => task.status === 'pending')
    .map(task => ({ ...task, kind: 'coding_revision', completed: false }));
  const nextLesson = lessons.findIndex(lesson => !lesson.completed);
  // Preserve lesson identities, order, completion flags and video progress.
  // Pending reviews go immediately before the next unfinished lesson.
  const position = nextLesson < 0 ? lessons.length : nextLesson;
  const learningPath = [...lessons.slice(0, position), ...revisions, ...lessons.slice(position)];
  return { learningPath, nextStep: learningPath.find(step => !step.completed) || null };
}

module.exports = { matchesCourse, tasksForCourse, buildLearningPath };
