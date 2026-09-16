// CodingAttempt.js

class CodingAttempt {
  constructor({ id, submissionId, startedAt, finishedAt, result }) {
    this.id = id;
    this.submissionId = submissionId;
    this.startedAt = startedAt;
    this.finishedAt = finishedAt;
    this.result = result || 'unknown';
  }
}

module.exports = CodingAttempt;
