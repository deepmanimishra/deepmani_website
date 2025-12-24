import os
import sqlite3
import smtplib
from email.mime.text import MIMEText
import google.generativeai as genai
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

# 1. Load Secrets
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "fallback_secret_key")

# 2. Secure Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

DB_PATH = "site.db"

# === DATABASE SETUP ===
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        # Standard Tables
        conn.execute('CREATE TABLE IF NOT EXISTS contacts (id INTEGER PRIMARY KEY, name TEXT, email TEXT, message TEXT, date TEXT)')
        conn.execute('CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY, title TEXT, description TEXT, category TEXT, image_url TEXT, likes INTEGER DEFAULT 0, date TEXT)')
        conn.execute('CREATE TABLE IF NOT EXISTS profile (id INTEGER PRIMARY KEY, profile_name TEXT, bio TEXT, sub_bio TEXT, profile_image TEXT)')
        
        # TABLES FOR YOUR EXISTING HTML (Journey & Docs)
        conn.execute('CREATE TABLE IF NOT EXISTS journey (id INTEGER PRIMARY KEY, year TEXT, title TEXT, description TEXT)')
        conn.execute('CREATE TABLE IF NOT EXISTS documents (id INTEGER PRIMARY KEY, title TEXT, file_path TEXT)')

        # Seed Profile if empty
        cur = conn.execute('SELECT * FROM profile WHERE id = 1')
        if not cur.fetchone():
            conn.execute('INSERT INTO profile (id, profile_name, bio, sub_bio, profile_image) VALUES (1, ?, ?, ?, ?)',
                         ("DEEPMANI MISHRA", "Student | IIT Madras", "Co-Founder | PRAMANIIK", "https://via.placeholder.com/150"))
        conn.commit()

init_db()

# === ROUTES COMPATIBLE WITH OLD HTML ===

@app.route('/')
def home():
    conn = get_db()
    # Fetch data to pass to your templates
    profile = conn.execute('SELECT * FROM profile WHERE id=1').fetchone()
    posts = conn.execute('SELECT * FROM posts ORDER BY id DESC').fetchall()
    journey = conn.execute('SELECT * FROM journey').fetchall()
    documents = conn.execute('SELECT * FROM documents').fetchall()
    
    # Render using your EXISTING templates
    return render_template("index.html", profile=profile, posts=posts, journey=journey, documents=documents)

@app.route('/dashboard')
def dashboard():
    if not session.get('admin'):
        return redirect(url_for('home'))
    return render_template("dashboard.html") # Assumes you have this file

# === ADMIN AUTH (Using Session for Old HTML compatibility) ===
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    if ADMIN_PASSWORD and data.get('password') == ADMIN_PASSWORD:
        session['admin'] = True
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Invalid Password"}), 401

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('home'))

# === FEATURES (AI, Contact, Posts) ===

@app.route('/api/smart_connect', methods=['POST'])
def smart_connect():
    if not GEMINI_API_KEY: return jsonify({"response": "API Key Config Missing"})
    data = request.json
    try:
        model = genai.GenerativeModel('gemini-pro')
        prompt = f"Draft a professional LinkedIn connection message from 'A Visitor' to 'Deepmani Mishra'. Context: {data['intent']}."
        response = model.generate_content(prompt)
        return jsonify({"response": response.text})
    except Exception as e:
        return jsonify({"response": "Error generating draft."})

@app.route('/api/chat', methods=['POST'])
def ai_chat():
    if not GEMINI_API_KEY: return jsonify({"response": "API Key Config Missing"})
    data = request.json
    try:
        model = genai.GenerativeModel('gemini-pro')
        chat = model.start_chat(history=[])
        response = chat.send_message(f"You are the AI of Deepmani Mishra. Answer briefly. User: {data['message']}")
        return jsonify({"response": response.text})
    except Exception as e:
        return jsonify({"response": "My brain is tired. Try again."})

@app.route('/api/contact', methods=['POST'])
def save_contact():
    d = request.json
    try:
        with get_db() as conn:
            conn.execute('INSERT INTO contacts (name, email, message, date) VALUES (?, ?, ?, ?)', 
                         (d['name'], d['email'], d['message'], datetime.now().strftime("%Y-%m-%d")))
            conn.commit()
            
        # Send Email
        if EMAIL_USER and EMAIL_PASS:
            msg = MIMEText(f"Name: {d['name']}\nEmail: {d['email']}\nMessage: {d['message']}")
            msg['Subject'] = f"Portfolio Contact: {d['name']}"
            msg['From'] = EMAIL_USER
            msg['To'] = EMAIL_RECEIVER or EMAIL_USER
            
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, EMAIL_RECEIVER or EMAIL_USER, msg.as_string())
            server.quit()
            
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"success": True, "warning": "Email failed"})

# === API FOR POSTS (Used by your JS) ===
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

if __name__ == "__main__":
    app.run(debug=True)