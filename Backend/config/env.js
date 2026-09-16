// env.js

require('dotenv').config();

module.exports = {
  port: process.env.PORT || 3000,
  dbConnection: process.env.DB_CONNECTION || 'mongodb://localhost:27017/coding_agent',
};
