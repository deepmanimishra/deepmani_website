import os
import sqlite3
import requests
import base64
import time
import re
import smtplib
import threading
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, g, jsonify, session, redirect, url_for, Response
from werkzeug.utils import secure_filename
from dotenv import load_dotenv  # <--- ADDED THIS

# Load secrets from .env file
load_dotenv()

app = Flask(__name__)
# Secure secret key
app.secret_key = os.environ.get("SECRET_KEY", "dev_key_fallback")
DATABASE = 'portfolio.db'
UPLOAD_FOLDER = 'static/uploads'

# --- CONFIGURATION (SECURED) ---
# We map standard Env names to your internal variable names
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
# Accepts either GMAIL_USER or EMAIL_USER
GMAIL_USER = os.environ.get("EMAIL_USER") or os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("EMAIL_PASS") or os.environ.get("GMAIL_APP_PASSWORD")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD") # <--- ADDED THIS

GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db():
    db = getattr(g, '_database', None)
    if db is None: db = g._database = sqlite3.connect(DATABASE); db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None: db.close()

# --- CRITICAL FIX FOR RENDER 500 ERROR ---
def init_db_command():
    if not os.path.exists(DATABASE):
        print("Creating Database for Render...")
        conn = sqlite3.connect(DATABASE)
        # Check if schema.sql exists, otherwise create tables manually to prevent crash
        if os.path.exists('schema.sql'):
            with app.open_resource('schema.sql', mode='r') as f:
                conn.cursor().executescript(f.read())
        else:
            # Emergency Schema Creation if file is missing
            c = conn.cursor()
            c.execute('CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY, title TEXT, description TEXT, category TEXT, image_url TEXT, likes INTEGER DEFAULT 0)')
            c.execute('CREATE TABLE IF NOT EXISTS journey (id INTEGER PRIMARY KEY, year TEXT, title TEXT, description TEXT)')
            c.execute('CREATE TABLE IF NOT EXISTS documents (id INTEGER PRIMARY KEY, title TEXT, file_path TEXT, uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
            c.execute('CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, name TEXT, email TEXT, message TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
            c.execute('CREATE TABLE IF NOT EXISTS followers (id INTEGER PRIMARY KEY, email TEXT, name TEXT, followed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
            c.execute('CREATE TABLE IF NOT EXISTS blocked_users (name TEXT UNIQUE)')
            c.execute('CREATE TABLE IF NOT EXISTS site_config (key TEXT PRIMARY KEY, value TEXT)')
        conn.commit()
        conn.close()
        print("Database Created Successfully.")

# EXECUTE IMMEDIATELY
init_db_command()

# --- SAFE PROFILE LOADER ---
@app.context_processor
def inject_profile():
    try:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        # Handle case where site_config table might not exist yet
        try:
            config = conn.execute('SELECT * FROM site_config').fetchall()
            profile_data = {row['key']: row['value'] for row in config}
        except:
            profile_data = {}
        conn.close()
        
        # Defaults if DB is empty
        if not profile_data:
            profile_data = {
                'profile_name': 'Deepmani Mishra',
                'profile_bio': 'Co-Founder | Pramaniik',
                'profile_image': 'https://scontent.fdbd5-1.fna.fbcdn.net/v/t39.30808-6/583332345_1532238231159902_8868260256540002026_n.jpg?_nc_cat=106&ccb=1-7&_nc_sid=6ee11a&_nc_ohc=1f5xHM5tN4IQ7kNvwGahYju&_nc_oc=AdmdrVjLwoi5QOvQIfNC_2bqwpUTQclSwrozc3LLXmspTqASm5dyTp5q1VfC1ULhNOt_RsJz-6h56-jT1VbpHI_I&_nc_zt=23&_nc_ht=scontent.fdbd5-1.fna&_nc_gid=J1l1FyZOC8Xzj7i0tSSPvg&oh=00_AflmiXEinKWylfA8rGKkrReIBDDR3TbQP5D7FnUhz1CSyQ&oe=693590AC'
            }
        return dict(profile=profile_data)
    except:
        return dict(profile={'profile_name': 'Deepmani Mishra', 'profile_bio': 'Co-Founder | Pramaniik', 'profile_image': '/static/profile.jpg'})

# --- EMAIL LOGIC ---
def send_email_async(to, sub, body):
    if not GMAIL_APP_PASSWORD or not GMAIL_USER: return
    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER; msg['To'] = to; msg['Subject'] = sub
    msg.attach(MIMEText(body, 'plain'))
    try:
        s = smtplib.SMTP('smtp.gmail.com', 587); s.starttls(); s.login(GMAIL_USER, GMAIL_APP_PASSWORD); s.send_message(msg); s.quit()
    except Exception as e: print(f"Email Error: {e}")

def trigger_email(to, sub, body): threading.Thread(target=send_email_async, args=(to, sub, body)).start()

def save_base64_image(data_url):
    try:
        if "base64," not in data_url: return None
        data = base64.b64decode(data_url.split(",", 1)[1])
        filename = f"img_{int(time.time())}.png"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        with open(filepath, "wb") as f: f.write(data)
        return f"/static/uploads/{filename}"
    except: return None

@app.route('/')
def index():
    db = get_db()
    return render_template('index.html', 
        posts=db.execute('SELECT * FROM posts ORDER BY id DESC').fetchall(),
        journey=db.execute('SELECT * FROM journey ORDER BY year DESC').fetchall(),
        documents=db.execute('SELECT * FROM documents ORDER BY uploaded_at DESC').fetchall(),
        categories=["Tech", "Startup", "Research", "Achievements", "Personal"])

@app.route('/dashboard')
def dashboard():
    if not session.get('admin'): return redirect(url_for('index'))
    db = get_db()
    return render_template('dashboard.html', 
        posts=db.execute('SELECT * FROM posts ORDER BY id DESC').fetchall(),
        journey=db.execute('SELECT * FROM journey ORDER BY year DESC').fetchall(),
        documents=db.execute('SELECT * FROM documents ORDER BY uploaded_at DESC').fetchall(),
        messages=db.execute('SELECT * FROM messages ORDER BY created_at DESC').fetchall(),
        followers=db.execute('SELECT * FROM followers ORDER BY followed_at DESC').fetchall())

# --- HYBRID AI CHAT ---
@app.route('/api/gemini', methods=['POST'])
def gemini_chat():
    data = request.json
    user = data.get('user', 'Guest')
    prompt = data.get('prompt')
    
    # 1. Try Real AI
    if GEMINI_API_KEY:
        try:
            sys = f"You are Deepmani Mishra. User: {user}. Keep answers short & professional."
            res = requests.post(GEMINI_API_URL, json={"contents": [{"parts": [{"text": prompt}]}], "systemInstruction": {"parts": [{"text": sys}]}}, headers={'Content-Type': 'application/json'})
            if res.status_code == 200:
                return jsonify({'response': res.json()['candidates'][0]['content']['parts'][0]['text']})
        except: pass

    # 2. Simulation Mode (Fallback)
    msg = prompt.lower()
    if any(x in msg for x in ['hi', 'hello']): reply = f"Hello {user}! I am Deepmani's AI. How can I help?"
    elif any(x in msg for x in ['work', 'project']): reply = "I Co-founded PRAMANIIK to solve cyber security challenges."
    elif any(x in msg for x in ['contact', 'email']): reply = "You can message me directly using the 'Get in Touch' button."
    elif "draft" in msg: reply = f"Hi Deepmani,\n\nI'd like to discuss a project.\n\nBest,\n{user}"
    else: reply = "That's interesting! I focus mostly on Deepmani's professional work. Ask me about my projects or research."
    
    time.sleep(1)
    return jsonify({'response': reply})

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    # --- SECURE FIX: Check Env Variable instead of hardcoded string ---
    pwd = request.json.get('password')
    if ADMIN_PASSWORD and pwd == ADMIN_PASSWORD: 
        session['admin'] = True
        return jsonify({'status': 'success'})
    # Fallback for local testing if env var is missing
    elif not ADMIN_PASSWORD and pwd == 'admin123': 
        session['admin'] = True
        return jsonify({'status': 'success'})
        
    return jsonify({'status': 'error'}), 401

@app.route('/api/admin/logout')
def admin_logout(): session.clear(); return redirect(url_for('index'))

@app.route('/api/admin/reply', methods=['POST'])
def admin_reply():
    if not session.get('admin'): return jsonify({'error': '403'}), 403
    d = request.json
    trigger_email(d['email'], f"Reply from Deepmani: {d['subject']}", d['message'])
    return jsonify({'status': 'success'})

@app.route('/api/admin/block', methods=['POST'])
def block_user():
    if not session.get('admin'): return jsonify({'error': '403'}), 403
    get_db().execute('INSERT OR IGNORE INTO blocked_users (name) VALUES (?)', (request.json['name'],)).connection.commit()
    return jsonify({'status': 'success'})

@app.route('/api/posts', methods=['POST'])
def create_post():
    if not session.get('admin'): return jsonify({'error': '403'}), 403
    d = request.json
    img = save_base64_image(d.get('imageUrl', '')) if 'base64' in d.get('imageUrl', '') else ''
    get_db().execute('INSERT INTO posts (title, description, image_url, category) VALUES (?, ?, ?, ?)', (d['title'], d['description'], img, d['category'])).connection.commit()
    return jsonify({'status': 'success'})

@app.route('/api/posts/<int:id>', methods=['DELETE'])
def delete_post(id):
    if not session.get('admin'): return jsonify({'error': '403'}), 403
    get_db().execute('DELETE FROM posts WHERE id = ?', (id,)).connection.commit()
    return jsonify({'status': 'success'})

@app.route('/api/journey', methods=['POST'])
def add_journey():
    if not session.get('admin'): return jsonify({'error': '403'}), 403
    d = request.json
    get_db().execute('INSERT INTO journey (year, title, description) VALUES (?, ?, ?)', (d['year'], d['title'], d['description'])).connection.commit()
    return jsonify({'status': 'success'})

@app.route('/api/journey/<int:id>', methods=['DELETE'])
def delete_journey(id):
    if not session.get('admin'): return jsonify({'error': '403'}), 403
    get_db().execute('DELETE FROM journey WHERE id = ?', (id,)).connection.commit()
    return jsonify({'status': 'success'})

@app.route('/api/documents', methods=['POST'])
def upload_doc():
    if not session.get('admin'): return jsonify({'error': '403'}), 403
    f = request.files['file']
    filename = secure_filename(f.filename)
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    f.save(path)
    web_path = f"/static/uploads/{filename}"
    get_db().execute('INSERT INTO documents (title, file_path) VALUES (?, ?)', (request.form['title'], web_path)).connection.commit()
    return jsonify({'status': 'success'})

@app.route('/api/documents/<int:id>', methods=['DELETE'])
def delete_doc(id):
    if not session.get('admin'): return jsonify({'error': '403'}), 403
    get_db().execute('DELETE FROM documents WHERE id = ?', (id,)).connection.commit()
    return jsonify({'status': 'success'})

@app.route('/api/contact', methods=['POST'])
def contact():
    d = request.json
    if get_db().execute('SELECT name FROM blocked_users WHERE name = ?', (d['name'],)).fetchone(): return jsonify({'status': 'error', 'message': 'Blocked.'})
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', d['email']): return jsonify({'status': 'error', 'message': 'Invalid Email Format'})
    
    get_db().execute('INSERT INTO messages (name, email, message) VALUES (?, ?, ?)', (d['name'], d['email'], d['message'])).connection.commit()
    trigger_email(GMAIL_USER, f"Contact: {d['name']}", f"From: {d['name']} ({d['email']})\n\n{d['message']}")
    return jsonify({'status': 'success', 'message': 'Message Sent!'})

@app.route('/api/follow', methods=['POST'])
def follow():
    d = request.json
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', d['email']): return jsonify({'status': 'error', 'message': 'Invalid Email'})
    try:
        get_db().execute('INSERT INTO followers (email, name) VALUES (?, ?)', (d['email'], d['name'])).connection.commit()
        trigger_email(GMAIL_USER, "New Follower", f"{d['name']} ({d['email']}) is now following you.")
        return jsonify({'status': 'success', 'message': 'Followed!'})
    except: return jsonify({'status': 'error', 'message': 'Already following.'})

@app.route('/api/posts/<int:id>/like', methods=['POST'])
def like(id):
    if get_db().execute('SELECT name FROM blocked_users WHERE name = ?', (request.json.get('user'),)).fetchone(): return jsonify({'error': 'Blocked'})
    get_db().execute('UPDATE posts SET likes = likes + 1 WHERE id = ?', (id,)).connection.commit()
    return jsonify({'likes': get_db().execute('SELECT likes FROM posts WHERE id = ?', (id,)).fetchone()['likes']})

@app.route('/api/posts/<int:id>/comments', methods=['GET', 'POST'])
def comments(id):
    if request.method == 'POST':
        d = request.json
        if get_db().execute('SELECT name FROM blocked_users WHERE name = ?', (d['author'],)).fetchone(): return jsonify({'error': 'Blocked'})
        get_db().execute('INSERT INTO comments (post_id, author_name, author_initial, content) VALUES (?, ?, ?, ?)', (id, d['author'], d['author_initial'], d['text'])).connection.commit()
        return jsonify({'status': 'success'})
    return jsonify([dict(r) for r in get_db().execute('SELECT * FROM comments WHERE post_id = ? ORDER BY created_at DESC', (id,)).fetchall()])

if __name__ == '__main__':
    # We still keep this for local testing
    app.run(debug=True, port=5000)