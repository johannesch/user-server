DROP TABLE IF EXISTS users;
CREATE TABLE users (
  id integer PRIMARY KEY autoincrement,
  name string UNIQUE NOT NULL,
  email string NOT NULL,
  password string NOT NULL
);
CREATE UNIQUE INDEX name_index ON users (name);