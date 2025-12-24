import os
import sqlite3
import smtplib
from email.mime.text import MIMEText
import google.generativeai as genai
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.utils import secure_filename

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "deepmani_secure_key")

# --- CONFIGURATION ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER") or EMAIL_USER

# Upload Config
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize AI
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')

DB_PATH = "site.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        # Create all tables required by your app.js features
        conn.execute('CREATE TABLE IF NOT EXISTS profile (id INTEGER PRIMARY KEY, profile_name TEXT, bio TEXT, sub_bio TEXT, profile_image TEXT)')
        conn.execute('CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY, title TEXT, description TEXT, category TEXT, image_url TEXT, likes INTEGER DEFAULT 0, date TEXT)')
        conn.execute('CREATE TABLE IF NOT EXISTS comments (id INTEGER PRIMARY KEY, post_id INTEGER, author TEXT, author_initial TEXT, content TEXT, date TEXT)')
        conn.execute('CREATE TABLE IF NOT EXISTS journey (id INTEGER PRIMARY KEY, year TEXT, title TEXT, description TEXT)')
        conn.execute('CREATE TABLE IF NOT EXISTS documents (id INTEGER PRIMARY KEY, title TEXT, file_path TEXT)')
        conn.execute('CREATE TABLE IF NOT EXISTS contacts (id INTEGER PRIMARY KEY, name TEXT, email TEXT, message TEXT, date TEXT)')
        conn.execute('CREATE TABLE IF NOT EXISTS subscribers (id INTEGER PRIMARY KEY, name TEXT, email TEXT)')

        # FIX 1: Ensure Profile Data Exists (Fixes "Profile picture not showing")
        cur = conn.execute('SELECT * FROM profile WHERE id = 1')
        if not cur.fetchone():
            conn.execute('INSERT INTO profile (id, profile_name, bio, sub_bio, profile_image) VALUES (1, ?, ?, ?, ?)',
                         ("DEEPMANI MISHRA", "Student | IIT Madras", "Co-Founder | PRAMANIIK", 
                          "https://scontent.fdbd5-1.fna.fbcdn.net/v/t39.30808-6/583332345_1532238231159902_8868260256540002026_n.jpg?_nc_cat=106&ccb=1-7&_nc_sid=6ee11a&_nc_ohc=1f5xHM5tN4IQ7kNvwGahYju&_nc_oc=AdmdrVjLwoi5QOvQIfNC_2bqwpUTQclSwrozc3LLXmspTqASm5dyTp5q1VfC1ULhNOt_RsJz-6h56-jT1VbpHI_I&_nc_zt=23&_nc_ht=scontent.fdbd5-1.fna&_nc_gid=J1l1FyZOC8Xzj7i0tSSPvg&oh=00_AflmiXEinKWylfA8rGKkrReIBDDR3TbQP5D7FnUhz1CSyQ&oe=693590AC"))

        # FIX 2: Restore Welcome Post
        cur = conn.execute('SELECT * FROM posts WHERE title = ?', ("Welcome to my Portfolio",))
        if not cur.fetchone():
            conn.execute('INSERT INTO posts (title, description, category, image_url, likes, date) VALUES (?, ?, ?, ?, ?, ?)',
                         ("Welcome to my Portfolio", "This is the start of my journey sharing my work in Data Science and AI.", "Highlight", "https://images.unsplash.com/photo-1555066931-4365d14bab8c?q=80&w=1000&auto=format&fit=crop", 10, datetime.now().strftime("%b %Y")))
        conn.commit()

init_db()

# --- PAGE ROUTES ---

@app.route('/')
def home():
    conn = get_db()
    # Pass all data to your EXISTING index.html template
    profile = conn.execute('SELECT * FROM profile WHERE id=1').fetchone()
    posts = conn.execute('SELECT * FROM posts ORDER BY id DESC').fetchall()
    journey = conn.execute('SELECT * FROM journey').fetchall()
    documents = conn.execute('SELECT * FROM documents').fetchall()
    return render_template("index.html", profile=profile, posts=posts, journey=journey, documents=documents)

@app.route('/dashboard')
def dashboard():
    if not session.get('admin'): return redirect(url_for('home'))
    return render_template("dashboard.html")

# --- API ROUTES (MATCHING YOUR JS EXACTLY) ---

# 1. Admin Login (JS calls /api/admin/login)
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.json
    if ADMIN_PASSWORD and data.get('password') == ADMIN_PASSWORD:
        session['admin'] = True
        return jsonify({"status": "success"})
    return jsonify({"status": "error"})

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('home'))

# 2. AI Chat (JS calls /api/gemini)
@app.route('/api/gemini', methods=['POST'])
def gemini_route():
    if not GEMINI_API_KEY: return jsonify({"response": "Error: API Key Missing"})
    data = request.json
    user_prompt = data.get('prompt')
    
    try:
        if "Draft a note:" in user_prompt:
            # Smart Connect Mode
            response = model.generate_content(f"Draft a LinkedIn message based on: {user_prompt.replace('Draft a note:', '')}")
        else:
            # Chat Mode
            chat = model.start_chat(history=[])
            response = chat.send_message(f"Answer briefly as Deepmani's AI. User: {user_prompt}")
            
        return jsonify({"response": response.text})
    except:
        return jsonify({"response": "AI Unavailable right now."})

# 3. Follow System (JS calls /api/follow)
@app.route('/api/follow', methods=['POST'])
def follow():
    d = request.json
    try:
        with get_db() as conn:
            conn.execute('INSERT INTO subscribers (name, email) VALUES (?, ?)', (d['name'], d['email']))
            conn.commit()
        return jsonify({"status": "success", "message": "Subscribed successfully!"})
    except:
        return jsonify({"status": "error", "message": "Error subscribing"})

# 4. Contact (JS calls /api/contact)
@app.route('/api/contact', methods=['POST'])
def contact():
    d = request.json
    with get_db() as conn:
        conn.execute('INSERT INTO contacts (name, email, message, date) VALUES (?, ?, ?, ?)', 
                     (d['name'], d['email'], d.get('message', ''), datetime.now().strftime("%Y-%m-%d")))
        conn.commit()
    # Email logic
    if EMAIL_USER and EMAIL_PASS:
        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            msg = MIMEText(f"Message from {d['name']} ({d['email']}):\n\n{d.get('message')}")
            msg['Subject'] = f"Portfolio Contact: {d['name']}"
            msg['From'] = EMAIL_USER
            msg['To'] = EMAIL_RECEIVER or EMAIL_USER
            server.sendmail(EMAIL_USER, EMAIL_RECEIVER or EMAIL_USER, msg.as_string())
            server.quit()
        except: pass
    return jsonify({"status": "success"})

# 5. Posts, Likes & Comments
@app.route('/api/posts', methods=['POST'])
def add_post():
    if not session.get('admin'): return jsonify({"error": "Unauthorized"}), 403
    d = request.json
    with get_db() as conn:
        conn.execute('INSERT INTO posts (title, description, category, image_url, likes, date) VALUES (?, ?, ?, ?, 0, ?)',
                     (d['title'], d.get('description'), d.get('category', 'General'), d.get('imageUrl'), datetime.now().strftime("%b %Y")))
        conn.commit()
    return jsonify({"success": True})

@app.route('/api/posts/<int:id>', methods=['DELETE'])
def delete_post(id):
    if not session.get('admin'): return jsonify({"error": "Unauthorized"}), 403
    with get_db() as conn:
        conn.execute('DELETE FROM posts WHERE id = ?', (id,))
        conn.commit()
    return jsonify({"success": True})

@app.route('/api/posts/<int:id>/like', methods=['POST'])
def like_post(id):
    with get_db() as conn:
        conn.execute('UPDATE posts SET likes = likes + 1 WHERE id = ?', (id,))
        conn.commit()
        row = conn.execute('SELECT likes FROM posts WHERE id = ?', (id,)).fetchone()
    return jsonify({"likes": row['likes']})

@app.route('/api/posts/<int:id>/comments', methods=['GET', 'POST'])
def comments(id):
    conn = get_db()
    if request.method == 'POST':
        d = request.json
        conn.execute('INSERT INTO comments (post_id, author, author_initial, content, date) VALUES (?, ?, ?, ?, ?)',
                     (id, d['author'], d['author_initial'], d['text'], datetime.now().strftime("%Y-%m-%d")))
        conn.commit()
        return jsonify({"success": True})
    rows = conn.execute('SELECT * FROM comments WHERE post_id = ? ORDER BY id DESC', (id,)).fetchall()
    return jsonify([dict(row) for row in rows])

# 6. Journey & Docs
@app.route('/api/journey', methods=['POST'])
def add_journey():
    if not session.get('admin'): return jsonify({"error": "Unauthorized"}), 403
    d = request.json
    with get_db() as conn:
        conn.execute('INSERT INTO journey (year, title, description) VALUES (?, ?, ?)', (d['year'], d['title'], d['description']))
        conn.commit()
    return jsonify({"success": True})

@app.route('/api/journey/<int:id>', methods=['DELETE'])
def delete_journey(id):
    if not session.get('admin'): return jsonify({"error": "Unauthorized"}), 403
    with get_db() as conn:
        conn.execute('DELETE FROM journey WHERE id = ?', (id,))
        conn.commit()
    return jsonify({"success": True})

@app.route('/api/documents', methods=['POST'])
def add_doc():
    if not session.get('admin'): return jsonify({"error": "Unauthorized"}), 403
    if 'file' in request.files:
        f = request.files['file']
        path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename))
        f.save(path)
        with get_db() as conn:
            conn.execute('INSERT INTO documents (title, file_path) VALUES (?, ?)', (request.form['title'], f"/static/uploads/{secure_filename(f.filename)}"))
            conn.commit()
    return jsonify({"success": True})

@app.route('/api/documents/<int:id>', methods=['DELETE'])
def delete_doc(id):
    if not session.get('admin'): return jsonify({"error": "Unauthorized"}), 403
    with get_db() as conn:
        conn.execute('DELETE FROM documents WHERE id = ?', (id,))
        conn.commit()
    return jsonify({"success": True})

if __name__ == "__main__":
    app.run(debug=True)