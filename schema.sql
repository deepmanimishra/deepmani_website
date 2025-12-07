DROP TABLE IF EXISTS posts;
DROP TABLE IF EXISTS comments;
DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS site_config;
DROP TABLE IF EXISTS journey;
DROP TABLE IF EXISTS documents;
DROP TABLE IF EXISTS blocked_users;
DROP TABLE IF EXISTS followers;

CREATE TABLE posts (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, description TEXT, image_url TEXT, category TEXT, likes INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE comments (id INTEGER PRIMARY KEY, post_id INTEGER, author_name TEXT, author_initial TEXT, content TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE messages (id INTEGER PRIMARY KEY, name TEXT, email TEXT, message TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE journey (id INTEGER PRIMARY KEY, year TEXT, title TEXT, description TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE documents (id INTEGER PRIMARY KEY, title TEXT, file_path TEXT, uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE blocked_users (name TEXT PRIMARY KEY);
CREATE TABLE followers (email TEXT PRIMARY KEY, name TEXT, followed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE site_config (key TEXT PRIMARY KEY, value TEXT);

-- Initial Data
INSERT INTO site_config VALUES ('profile_name', 'Deepmani Mishra'), ('profile_bio', 'Student | IIT Madras'), ('profile_image', '/static/profile.jpg');
INSERT INTO posts (title, description, category, likes, image_url) VALUES ('Welcome!', 'Welcome to my 3D Portfolio.', 'Personal', 10, '');