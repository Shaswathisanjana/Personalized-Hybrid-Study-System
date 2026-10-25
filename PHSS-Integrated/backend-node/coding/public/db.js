(function (root) {
  'use strict';
  const opened = new Promise((resolve, reject) => {
    const request = indexedDB.open('cacm-python-practice', 1);
    request.onupgradeneeded = () => {
      const db = request.result;
      const attempts = db.createObjectStore('attempts', { keyPath: 'key' });
      attempts.createIndex('userId', 'userId');
      db.createObjectStore('values', { keyPath: 'key' });
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
    request.onblocked = () => reject(new Error('Close other practice tabs to finish the storage upgrade.'));
  });
  async function operate(storeName, mode, makeRequest) {
    const db = await opened;
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(storeName, mode);
      const request = makeRequest(transaction.objectStore(storeName));
      transaction.oncomplete = () => resolve(request.result);
      transaction.onerror = () => reject(transaction.error || request.error);
      transaction.onabort = () => reject(transaction.error || new Error('Local save was interrupted.'));
    });
  }
  root.PracticeDB = {
    saveAttempt: attempt => operate('attempts', 'readwrite', store => store.put({ ...attempt, key: `${attempt.userId}:${attempt.attemptId}` })),
    attempts: userId => operate('attempts', 'readonly', store => store.index('userId').getAll(userId)),
    set: (key, value) => operate('values', 'readwrite', store => store.put({ key, value })),
    get: async key => (await operate('values', 'readonly', store => store.get(key)))?.value
  };
})(globalThis);
