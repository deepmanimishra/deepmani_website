import os
import sqlite3
import mimetypes  # <--- IMPORTANT: Added for 3D site support
from dotenv import load_dotenv

load_dotenv()

import smtplib
from email.mime.text import MIMEText
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Needed for flash messages

# === IMPORTANT: Fix for 3D Website Files ===
# This tells the server that .glb files are 3D models, not text.
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('model/gltf-binary', '.glb')
mimetypes.add_type('model/gltf+json', '.gltf')

# === SQLite Configuration ===
DB_PATH = "site.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# === Create table if it doesn't exist ===
def init_db():
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                message TEXT NOT NULL
            )
        ''')
        conn.commit()

init_db()

@app.route('/')
def home():
    # This renders your new 3D index.html
    return render_template("index.html")

# --- COMMENTED OUT ROUTES (Saved for later) ---
# @app.route('/about')
# def about():
#     return render_template("about.html")

# @app.route('/projects')
# def projects():
#     return render_template("projects.html")

# @app.route('/resume')
# def resume():
#     return render_template("resume.html")

# @app.route('/contact', methods=['GET', 'POST'])
# def contact():
#     # ... (Your previous contact logic) ...
#     return render_template("contact.html")

@app.route('/robots.txt')
def robots():
    return app.send_static_file('robots.txt')

@app.route('/sitemap.xml')
def sitemap():
    pages = []
    # UPDATE THIS URL to your actual domain if different
    base_url = 'https://deepmanimishra.onrender.com'

    for rule in app.url_map.iter_rules():
        if "GET" in rule.methods and not rule.arguments:
            # We filter out static files to keep sitemap clean
            if "/static/" not in rule.rule:
                pages.append(f"{base_url}{rule.rule}")

    sitemap_xml = '<?xml version="1.0" encoding="UTF-8"?>'
    sitemap_xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    for page in pages:
        sitemap_xml += f'<url><loc>{page}</loc></url>'
    sitemap_xml += '</urlset>'

    return sitemap_xml, 200, {'Content-Type': 'application/xml'}

if __name__ == "__main__":
    app.run(debug=True)