import os
import sqlite3
import mimetypes
import google.generativeai as genai
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify

load_dotenv()

app = Flask(__name__)
app.secret_key = "supersecretkey"

# === CONFIGURATION ===
# Ensure this matches the key you added in Render
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('model/gltf-binary', '.glb')

DB_PATH = "site.db"

# === DATABASE SETUP ===
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        # Contacts & Posts
        conn.execute('CREATE TABLE IF NOT EXISTS contacts (id INTEGER PRIMARY KEY, name TEXT, email TEXT, message TEXT, date TEXT)')
        conn.execute('CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY, title TEXT, description TEXT, category TEXT, image_url TEXT, likes INTEGER DEFAULT 0, date TEXT)')
        
        # Profile Table (For editable Bio/Image)
        conn.execute('CREATE TABLE IF NOT EXISTS profile (id INTEGER PRIMARY KEY, name TEXT, bio TEXT, sub_bio TEXT, image_url TEXT)')
        
        # Seed Profile if empty
        cur = conn.execute('SELECT * FROM profile WHERE id = 1')
        if not cur.fetchone():
            conn.execute('INSERT INTO profile (id, name, bio, sub_bio, image_url) VALUES (1, ?, ?, ?, ?)',
                         ("DEEPMANI MISHRA", "Student | IIT Madras", "Co-Founder | PRAMAANIK", "https://scontent.fdbd5-1.fna.fbcdn.net/v/t39.30808-6/583332345_1532238231159902_8868260256540002026_n.jpg?_nc_cat=106&ccb=1-7&_nc_sid=6ee11a&_nc_ohc=1f5xHM5tN4IQ7kNvwGahYju&_nc_oc=AdmdrVjLwoi5QOvQIfNC_2bqwpUTQclSwrozc3LLXmspTqASm5dyTp5q1VfC1ULhNOt_RsJz-6h56-jT1VbpHI_I&_nc_zt=23&_nc_ht=scontent.fdbd5-1.fna&_nc_gid=J1l1FyZOC8Xzj7i0tSSPvg&oh=00_AflmiXEinKWylfA8rGKkrReIBDDR3TbQP5D7FnUhz1CSyQ&oe=693590AC"))
        
        conn.commit()

init_db()

# === ROUTES ===

@app.route('/')
def home(): return render_template("index.html")

# --- PROFILE API ---
@app.route('/api/profile', methods=['GET', 'POST'])
def handle_profile():
    conn = get_db()
    if request.method == 'POST':
        if request.headers.get('Admin-Key') != 'admin123': return jsonify({"error": "Unauthorized"}), 403
        d = request.json
        conn.execute('UPDATE profile SET name=?, bio=?, sub_bio=?, image_url=? WHERE id=1', 
                     (d['name'], d['bio'], d['sub_bio'], d['image']))
        conn.commit()
        return jsonify({"success": True})
    
    row = conn.execute('SELECT * FROM profile WHERE id=1').fetchone()
    return jsonify(dict(row))

# --- POSTS API (Get, Add, Edit, Delete) ---
@app.route('/api/posts', methods=['GET', 'POST'])
def handle_posts():
    conn = get_db()
    if request.method == 'POST': # Add Post
        if request.headers.get('Admin-Key') != 'admin123': return jsonify({"error": "Unauthorized"}), 403
        d = request.json
        conn.execute('INSERT INTO posts (title, description, category, image_url, date) VALUES (?, ?, ?, ?, ?)',
                     (d['title'], d['description'], d['category'], d['image'], datetime.now().strftime("%b %Y")))
        conn.commit()
        return jsonify({"success": True})
    
    posts = conn.execute('SELECT * FROM posts ORDER BY id DESC').fetchall()
    return jsonify([dict(row) for row in posts])

@app.route('/api/posts/<int:id>', methods=['PUT', 'DELETE'])
def modify_post(id):
    if request.headers.get('Admin-Key') != 'admin123': return jsonify({"error": "Unauthorized"}), 403
    conn = get_db()
    if request.method == 'DELETE':
        conn.execute('DELETE FROM posts WHERE id = ?', (id,))
    elif request.method == 'PUT':
        d = request.json
        conn.execute('UPDATE posts SET title=?, description=?, category=?, image_url=? WHERE id=?',
                     (d['title'], d['description'], d['category'], d['image'], id))
    conn.commit()
    return jsonify({"success": True})

@app.route('/api/like/<int:id>', methods=['POST'])
def like_post(id):
    with get_db() as conn:
        conn.execute('UPDATE posts SET likes = likes + 1 WHERE id = ?', (id,))
        conn.commit()
    return jsonify({"success": True})

# --- AI FEATURES ---
@app.route('/api/smart_connect', methods=['POST'])
def smart_connect():
    if not GEMINI_API_KEY: return jsonify({"response": "API Key Missing"})
    data = request.json
    try:
        model = genai.GenerativeModel('gemini-pro')
        prompt = f"Write a short, professional LinkedIn connection message from a visitor to Deepmani Mishra. Context: {data['intent']}."
        response = model.generate_content(prompt)
        return jsonify({"response": response.text})
    except Exception as e:
        return jsonify({"response": "Error generating text."})

@app.route('/api/chat', methods=['POST'])
def ai_chat():
    if not GEMINI_API_KEY: return jsonify({"response": "Error: API Key Missing"})
    data = request.json
    try:
        model = genai.GenerativeModel('gemini-pro')
        chat = model.start_chat(history=[])
        response = chat.send_message(f"You are the AI Assistant of Deepmani Mishra (Student IIT Madras). Keep answers short. User: {data['message']}")
        return jsonify({"response": response.text})
    except Exception as e:
        return jsonify({"response": "My brain is tired. Try again."})

@app.route('/api/contact', methods=['POST'])
def save_contact():
    d = request.json
    with get_db() as conn:
        conn.execute('INSERT INTO contacts (name, email, message, date) VALUES (?, ?, ?, ?)', (d['name'], d['email'], d['message'], datetime.now().strftime("%Y-%m-%d")))
        conn.commit()
    return jsonify({"success": True})

if __name__ == "__main__":
    app.run(debug=True)