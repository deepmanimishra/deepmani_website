import os
import psycopg2
import psycopg2.extras
import requests
import base64
import time
import re
import smtplib
import threading
from flask import Flask, render_template, request, g, jsonify, session, redirect, url_for
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev_key")

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

GMAIL_USER = os.environ.get("EMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("EMAIL_PASS")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

# ---------------- DB ---------------- #

def get_db():
    if 'db' not in g:
        g.db = psycopg2.connect(
            os.environ.get("DATABASE_URL"),
            sslmode='require'
        )
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db:
        db.close()

# ---------------- PROFILE ---------------- #

@app.context_processor
def inject_profile():
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("SELECT * FROM site_config")
        config = cur.fetchall()

        profile = {row['key']: row['value'] for row in config}

        if not profile:
            profile = {
                'profile_name': 'Deepmani Mishraa',
                'profile_bio': 'Portfolio',
                'profile_image': '/static/profile.jpg'
            }

        return dict(profile=profile)

    except:
        return dict(profile={
            'profile_name': 'Deepmani Mishraa',
            'profile_bio': 'Portfolio',
            'profile_image': '/static/profile.jpg'
        })

# ---------------- EMAIL ---------------- #

def send_email_async(to, sub, body):
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        return

    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = to
    msg['Subject'] = sub
    msg.attach(MIMEText(body, 'plain'))

    try:
        s = smtplib.SMTP('smtp.gmail.com', 587)
        s.starttls()
        s.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        s.send_message(msg)
        s.quit()
    except Exception as e:
        print("Email error:", e)

def trigger_email(to, sub, body):
    threading.Thread(target=send_email_async, args=(to, sub, body)).start()

# ---------------- IMAGE ---------------- #

def save_base64_image(data_url):
    if "base64," not in data_url:
        return None

    data = base64.b64decode(data_url.split(",", 1)[1])
    filename = f"img_{int(time.time())}.png"
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    with open(path, "wb") as f:
        f.write(data)

    return f"/static/uploads/{filename}"

# ---------------- ROUTES ---------------- #

@app.route('/')
def index():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cur.execute("SELECT * FROM posts ORDER BY id DESC")
        posts = cur.fetchall()
    except:
        posts = []

    try:
        cur.execute("SELECT * FROM journey ORDER BY year DESC")
        journey = cur.fetchall()
    except:
        journey = []

    try:
        cur.execute("SELECT * FROM documents ORDER BY uploaded_at DESC")
        documents = cur.fetchall()
    except:
        documents = []

    return render_template('index.html',
        posts=posts,
        journey=journey,
        documents=documents
    )

@app.route('/dashboard')
def dashboard():
    if not session.get('admin'):
        return redirect('/')

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT * FROM posts ORDER BY id DESC")
    posts = cur.fetchall()

    return render_template('dashboard.html', posts=posts)

# ---------------- ADMIN ---------------- #

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    pwd = request.json.get('password')

    if pwd == ADMIN_PASSWORD:
        session['admin'] = True
        return jsonify({'status': 'success'})

    return jsonify({'status': 'error'}), 401

# ---------------- POSTS ---------------- #

@app.route('/api/posts', methods=['POST'])
def create_post():
    if not session.get('admin'):
        return jsonify({'error': '403'}), 403

    d = request.json
    img = save_base64_image(d.get('imageUrl', '')) if 'base64' in d.get('imageUrl', '') else ''

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO posts (title, description, image_url, category) VALUES (%s, %s, %s, %s)",
        (d['title'], d['description'], img, d['category'])
    )

    conn.commit()
    return jsonify({'status': 'success'})

# ---------------- CONTACT ---------------- #

@app.route('/api/contact', methods=['POST'])
def contact():
    d = request.json

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO messages (name, email, message) VALUES (%s, %s, %s)",
        (d['name'], d['email'], d['message'])
    )

    conn.commit()

    trigger_email(
        GMAIL_USER,
        f"Message from {d['name']}",
        d['message']
    )

    return jsonify({'status': 'success'})

# ---------------- INIT DB ---------------- #

@app.route('/init-db')
def init_db():
    conn = get_db()
    cur = conn.cursor()

    with open('schema.sql', 'r') as f:
        cur.execute(f.read())

    conn.commit()
    return "DB Initialized"

# ---------------- RUN ---------------- #

if __name__ == '__main__':
    app.run(debug=True)