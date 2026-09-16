// CodingRoadmap.js

class CodingRoadmap {
  constructor({ id, title, steps }) {
    this.id = id;
    this.title = title;
    this.steps = steps || [];
  }
}

module.exports = CodingRoadmap;
