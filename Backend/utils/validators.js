// validators.js

exports.validateEmail = (email) => {
  return typeof email === 'string' && email.includes('@');
};
