// CodingSkill.js

class CodingSkill {
  constructor({ id, name, category, level }) {
    this.id = id;
    this.name = name;
    this.category = category;
    this.level = level || 'intermediate';
  }
}

module.exports = CodingSkill;
