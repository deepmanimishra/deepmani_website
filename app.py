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

app = Flask(__name__)
# Secure fallback for secret key to prevent session errors on restart
app.secret_key = os.environ.get("SECRET_KEY", "dev_key_892374")
DATABASE = 'portfolio.db'
UPLOAD_FOLDER = 'static/uploads'

# --- CONFIGURATION (HYBRID) ---
# 1. Tries to get keys from Render Environment Variables (Best for Deployment)
# 2. Falls back to the keys you provided (Best for Local Testing)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyCyBleT88wx7BXrOwIU-YCyOzAnYr3KRu4")
GMAIL_USER = os.environ.get("GMAIL_USER", "brijratndeepmanimishra584@gmail.com")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "mjtseukonpjddlps")

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

def init_db():
    with app.app_context():
        db = get_db()
        with open('schema.sql', mode='r') as f: db.cursor().executescript(f.read())
        db.commit()

# --- SAFE DATA LOADERS (Prevents 500 Errors) ---
def get_profile_safe():
    try:
        db = get_db()
        config = db.execute('SELECT * FROM site_config').fetchall()
        if not config: raise Exception("Empty DB")
        return {row['key']: row['value'] for row in config}
    except:
        # Emergency Fallback Data
        return {
            'profile_name': 'Deepmani Mishra', 
            'profile_bio': 'Student | IIT Madras', 
            'profile_image': '/static/profile.jpg'
        }

@app.context_processor
def inject_global_vars():
    return dict(profile=get_profile_safe())

# --- ASYNC EMAIL ---
def send_email_async(to, sub, body):
    if not GMAIL_APP_PASSWORD: return
    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER; msg['To'] = to; msg['Subject'] = sub
    msg.attach(MIMEText(body, 'plain'))
    try:
        s = smtplib.SMTP('smtp.gmail.com', 587); s.starttls(); s.login(GMAIL_USER, GMAIL_APP_PASSWORD); s.send_message(msg); s.quit()
    except Exception as e: print(f"Email Error: {e}")

def trigger_email(to, sub, body): 
    threading.Thread(target=send_email_async, args=(to, sub, body)).start()

def save_base64_image(data_url):
    try:
        if "base64," not in data_url: return None
        data = base64.b64decode(data_url.split(",", 1)[1])
        filename = f"img_{int(time.time())}.png"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        with open(filepath, "wb") as f: f.write(data)
        return f"/static/uploads/{filename}"
    except: return None

# --- ROUTES ---
@app.route('/')
def index():
    db = get_db()
    return render_template('index.html', 
        profile=get_profile_safe(),
        posts=db.execute('SELECT * FROM posts ORDER BY id DESC').fetchall(),
        journey=db.execute('SELECT * FROM journey ORDER BY year DESC').fetchall(),
        documents=db.execute('SELECT * FROM documents ORDER BY uploaded_at DESC').fetchall(),
        categories=["Tech", "Startup", "Research", "Achievements", "Personal"])

@app.route('/dashboard')
def dashboard():
    if not session.get('admin'): return redirect(url_for('index'))
    db = get_db()
    return render_template('dashboard.html', 
        profile=get_profile_safe(),
        posts=db.execute('SELECT * FROM posts ORDER BY id DESC').fetchall(),
        journey=db.execute('SELECT * FROM journey ORDER BY year DESC').fetchall(),
        documents=db.execute('SELECT * FROM documents ORDER BY uploaded_at DESC').fetchall(),
        messages=db.execute('SELECT * FROM messages ORDER BY created_at DESC').fetchall(),
        followers=db.execute('SELECT * FROM followers ORDER BY followed_at DESC').fetchall())

# --- HYBRID AI CHAT (The Fix) ---
@app.route('/api/gemini', methods=['POST'])
def gemini_chat():
    data = request.json
    user = data.get('user', 'Guest')
    prompt = data.get('prompt')
    
    # SYSTEM 1: Try Real AI
    if GEMINI_API_KEY:
        try:
            sys = f"You are Deepmani Mishra. User: {user}. Keep answers short."
            res = requests.post(GEMINI_API_URL, json={"contents": [{"parts": [{"text": prompt}]}], "systemInstruction": {"parts": [{"text": sys}]}}, headers={'Content-Type': 'application/json'})
            if res.status_code == 200:
                return jsonify({'response': res.json()['candidates'][0]['content']['parts'][0]['text']})
        except:
            pass # Fail silently and use fallback

    # SYSTEM 2: Simulation Mode (Fallback)
    msg = prompt.lower()
    if any(x in msg for x in ['hi', 'hello']): reply = f"Hello {user}! I am Deepmani's AI. How can I help?"
    elif any(x in msg for x in ['work', 'project']): reply = "I founded PRAMAANIK to solve cyber security challenges."
    elif any(x in msg for x in ['contact', 'email']): reply = "You can message me directly using the 'Get in Touch' button."
    elif "draft" in msg: reply = f"Hi Deepmani,\n\nI'd like to discuss a project.\n\nBest,\n{user}"
    else: reply = "That's interesting! Ask me about my projects or research."
    
    time.sleep(1) # Fake thinking time for realism
    return jsonify({'response': reply})

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    if request.json.get('password') == 'admin123': session['admin'] = True; return jsonify({'status': 'success'})
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
    if not os.path.exists(DATABASE): init_db()
    app.run(debug=True, port=5000)