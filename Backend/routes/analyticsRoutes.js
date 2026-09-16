// analyticsRoutes.js

const express = require('express');
const router = express.Router();

router.get('/', (req, res) => {
  res.status(200).json({ message: 'Analytics route' });
});

module.exports = router;
