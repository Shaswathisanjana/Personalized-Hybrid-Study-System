// roadmapRoutes.js

const express = require('express');
const router = express.Router();

router.get('/', (req, res) => {
  res.status(200).json({ message: 'Roadmap route' });
});

module.exports = router;
