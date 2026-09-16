// errorHandler.js

exports.handleError = (err, req, res, next) => {
  console.error(err);
  res.status(500).json({ error: 'Internal server error' });
};
