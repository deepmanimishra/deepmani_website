import os
import sqlite3
import mimetypes
import google.generativeai as genai
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

load_dotenv()

app = Flask(__name__)
app.secret_key = "supersecretkey"

# === 1. CONFIGURATION ===
# OPTION A: Get from .env file (Recommended)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 

# OPTION B: Paste directly here if .env fails (Delete this line for production!)
# GEMINI_API_KEY = "AIzaSy....." 

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# MIME types for 3D files
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('model/gltf-binary', '.glb')

DB_PATH = "site.db"

# === 2. DATABASE SETUP ===
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# REPLACE your existing init_db function with this:
def init_db():
    with get_db_connection() as conn:
        # 1. Create Contacts Table (You already have this)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                message TEXT NOT NULL,
                date TEXT
            )
        ''')

        # 2. Create Posts Table (NEW - Needed for Admin/Highlights)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                description TEXT,
                category TEXT,
                image_url TEXT,
                likes INTEGER DEFAULT 0,
                date TEXT
            )
        ''')
        
        conn.commit()
    print("Database initialized successfully.")

# === 3. ROUTES ===

@app.route('/')
def home():
    return render_template("index.html")

# --- API: GET POSTS ---
@app.route('/api/posts')
def get_posts():
    try:
        conn = get_db()
        posts = conn.execute('SELECT * FROM posts ORDER BY id DESC').fetchall()
        conn.close()
        return jsonify([dict(row) for row in posts])
    except Exception as e:
        return jsonify([])

# --- API: ADD POST (ADMIN) ---
@app.route('/api/add_post', methods=['POST'])
def add_post():
    if request.headers.get('Admin-Key') != 'admin123': 
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    with get_db() as conn:
        conn.execute('INSERT INTO posts (title, description, category, image_url, date) VALUES (?, ?, ?, ?, ?)',
                     (data['title'], data['description'], data['category'], data['image'], datetime.now().strftime("%b %Y")))
        conn.commit()
    return jsonify({"success": True})

# --- API: LIKE POST ---
@app.route('/api/like/<int:post_id>', methods=['POST'])
def like_post(post_id):
    with get_db() as conn:
        conn.execute('UPDATE posts SET likes = likes + 1 WHERE id = ?', (post_id,))
        conn.commit()
    return jsonify({"success": True})

# --- API: SAVE CONTACT MESSAGE ---
@app.route('/api/contact', methods=['POST'])
def save_contact():
    data = request.json
    try:
        with get_db() as conn:
            conn.execute('INSERT INTO contacts (name, email, message, date) VALUES (?, ?, ?, ?)',
                         (data['name'], data['email'], data['message'], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        print("Error saving contact:", e)
        return jsonify({"success": False}), 500

# --- API: AI CHAT ---
@app.route('/api/chat', methods=['POST'])
def ai_chat():
    if not GEMINI_API_KEY:
        return jsonify({"response": "I need a Gemini API Key to think! Tell Deepmani to add it."})
    
    data = request.json
    user_msg = data.get('message', '')
    
    # System Persona
    system_prompt = """You are the AI Avatar of Deepmani Mishra. 
    Deepmani is a Student at IIT Madras (BS in Data Science) and Co-Founder of PRAMAANIK.
    He loves Python, AI, and Entrepreneurship.
    Keep answers short, professional, and friendly."""
    
    try:
        model = genai.GenerativeModel('gemini-pro')
        chat = model.start_chat(history=[])
        response = chat.send_message(f"{system_prompt}\nUser Question: {user_msg}")
        return jsonify({"response": response.text})
    except Exception as e:
        print("Gemini Error:", e)
        return jsonify({"response": "My brain is tired. Please try again later."})

# --- SEO ROUTES ---
@app.route('/robots.txt')
def robots():
    return app.send_static_file('robots.txt')

if __name__ == "__main__":
    app.run(debug=True)