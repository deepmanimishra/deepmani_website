import os
import sqlite3
import smtplib
from email.mime.text import MIMEText
import google.generativeai as genai
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "deepmani_secure_key")

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

# Initialize AI once (Faster)
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
        # Create Tables
        conn.execute('CREATE TABLE IF NOT EXISTS profile (id INTEGER PRIMARY KEY, profile_name TEXT, bio TEXT, sub_bio TEXT, profile_image TEXT)')
        conn.execute('CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY, title TEXT, description TEXT, category TEXT, image_url TEXT, likes INTEGER DEFAULT 0, date TEXT)')
        conn.execute('CREATE TABLE IF NOT EXISTS journey (id INTEGER PRIMARY KEY, year TEXT, title TEXT, description TEXT)')
        conn.execute('CREATE TABLE IF NOT EXISTS documents (id INTEGER PRIMARY KEY, title TEXT, file_path TEXT)')
        conn.execute('CREATE TABLE IF NOT EXISTS contacts (id INTEGER PRIMARY KEY, name TEXT, email TEXT, message TEXT, date TEXT)')

        # --- FIX 1: RESTORE YOUR REAL PROFILE ---
        cur = conn.execute('SELECT * FROM profile WHERE id = 1')
        if not cur.fetchone():
            conn.execute('INSERT INTO profile (id, profile_name, bio, sub_bio, profile_image) VALUES (1, ?, ?, ?, ?)',
                         ("DEEPMANI MISHRA", "Student | IIT Madras", "Co-Founder | PRAMANIIK", 
                          "https://scontent.fdbd5-1.fna.fbcdn.net/v/t39.30808-6/583332345_1532238231159902_8868260256540002026_n.jpg?_nc_cat=106&ccb=1-7&_nc_sid=6ee11a&_nc_ohc=1f5xHM5tN4IQ7kNvwGahYju&_nc_oc=AdmdrVjLwoi5QOvQIfNC_2bqwpUTQclSwrozc3LLXmspTqASm5dyTp5q1VfC1ULhNOt_RsJz-6h56-jT1VbpHI_I&_nc_zt=23&_nc_ht=scontent.fdbd5-1.fna&_nc_gid=J1l1FyZOC8Xzj7i0tSSPvg&oh=00_AflmiXEinKWylfA8rGKkrReIBDDR3TbQP5D7FnUhz1CSyQ&oe=693590AC"))

        # --- FIX 2: RESTORE WELCOME POST ---
        cur = conn.execute('SELECT * FROM posts WHERE title = ?', ("Welcome to my Portfolio",))
        if not cur.fetchone():
            conn.execute('INSERT INTO posts (title, description, category, image_url, likes, date) VALUES (?, ?, ?, ?, ?, ?)',
                         ("Welcome to my Portfolio", "This is the start of my journey sharing my work in Data Science and AI.", "Highlight", "https://images.unsplash.com/photo-1555066931-4365d14bab8c?q=80&w=1000&auto=format&fit=crop", 10, "Dec 2025"))
        conn.commit()

init_db()

# --- ROUTES ---

@app.route('/')
def home():
    conn = get_db()
    profile = conn.execute('SELECT * FROM profile WHERE id=1').fetchone()
    posts = conn.execute('SELECT * FROM posts ORDER BY id DESC').fetchall()
    journey = conn.execute('SELECT * FROM journey').fetchall()
    documents = conn.execute('SELECT * FROM documents').fetchall()
    return render_template("index.html", profile=profile, posts=posts, journey=journey, documents=documents)

@app.route('/dashboard')
def dashboard():
    if not session.get('admin'):
        return redirect(url_for('home'))
    return render_template("dashboard.html")

# --- ADMIN LOGIN (Fixes Admin System) ---
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    # Checks environment variable securely
    if ADMIN_PASSWORD and data.get('password') == ADMIN_PASSWORD:
        session['admin'] = True
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Incorrect Password"}), 401

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('home'))

# --- AI CHAT (Fixes Slowness) ---
@app.route('/api/chat', methods=['POST'])
def ai_chat():
    if not GEMINI_API_KEY: 
        return jsonify({"response": "System Error: AI Key Missing"})
    
    data = request.json
    try:
        # Use global model instance to be faster
        chat = model.start_chat(history=[])
        response = chat.send_message(f"You are the AI of Deepmani Mishra. Keep answers under 2 sentences. User: {data['message']}")
        return jsonify({"response": response.text})
    except Exception as e:
        return jsonify({"response": "I am rebooting. Try again in 5 seconds."})

@app.route('/api/smart_connect', methods=['POST'])
def smart_connect():
    if not GEMINI_API_KEY: return jsonify({"response": "Config Error"})
    data = request.json
    try:
        response = model.generate_content(f"Draft a short LinkedIn message for Deepmani. Context: {data['intent']}")
        return jsonify({"response": response.text})
    except:
        return jsonify({"response": "Error generating draft."})

# --- POST API (For Admin Dashboard) ---
@app.route('/api/posts', methods=['POST'])
def add_post():
    if not session.get('admin'): return jsonify({"error": "Unauthorized"}), 403
    d = request.json
    with get_db() as conn:
        conn.execute('INSERT INTO posts (title, description, category, image_url, likes, date) VALUES (?, ?, ?, ?, 0, ?)',
                     (d['title'], d['description'], d.get('category', 'General'), d['image'], datetime.now().strftime("%b %Y")))
        conn.commit()
    return jsonify({"success": True})

@app.route('/api/posts/<int:id>', methods=['DELETE'])
def delete_post(id):
    if not session.get('admin'): return jsonify({"error": "Unauthorized"}), 403
    with get_db() as conn:
        conn.execute('DELETE FROM posts WHERE id = ?', (id,))
        conn.commit()
    return jsonify({"success": True})

# --- EMAIL CONTACT ---
@app.route('/api/contact', methods=['POST'])
def save_contact():
    d = request.json
    try:
        with get_db() as conn:
            conn.execute('INSERT INTO contacts (name, email, message, date) VALUES (?, ?, ?, ?)', 
                         (d['name'], d['email'], d['message'], datetime.now().strftime("%Y-%m-%d")))
            conn.commit()
        
        if EMAIL_USER and EMAIL_PASS:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            msg = MIMEText(f"From: {d['name']} ({d['email']})\n\n{d['message']}")
            msg['Subject'] = f"Portfolio Message: {d['name']}"
            msg['From'] = EMAIL_USER
            msg['To'] = EMAIL_RECEIVER or EMAIL_USER
            server.sendmail(EMAIL_USER, EMAIL_RECEIVER or EMAIL_USER, msg.as_string())
            server.quit()
            
        return jsonify({"success": True})
    except:
        return jsonify({"success": True, "warning": "Saved to DB, Email Failed"})

if __name__ == "__main__":
    app.run(debug=True)