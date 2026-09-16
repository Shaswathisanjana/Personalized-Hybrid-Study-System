// User.js

class User {
  constructor({ id, name, email, role }) {
    this.id = id;
    this.name = name;
    this.email = email;
    this.role = role || 'student';
  }
}

module.exports = User;
