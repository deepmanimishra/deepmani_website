import os
from dotenv import load_dotenv

load_dotenv()

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Needed for flash messages

# MySQL Configuration
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="D.M.Babu@95087",
    database="deepmani_site"
)
cursor = db.cursor()

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/about')
def about():
    return render_template("about.html")

@app.route('/projects')
def projects():
    return render_template("projects.html")

@app.route('/resume')
def resume():
    return render_template("resume.html")

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        message = request.form.get('message', '').strip()

        if not name or not email or not message:
            flash("All fields are required.", "error")
            return redirect(url_for('contact'))

        try:
            # Save to database
            cursor.execute("INSERT INTO contacts (name, email, message) VALUES (%s, %s, %s)", (name, email, message))
            db.commit()

            # Send email notification
            send_email_notification(name, email, message)

            flash("Thank you! Your message has been sent.", "success")
        except Exception as e:
            print("Database or email error:", e)
            flash("Something went wrong. Please try again later.", "error")

        return redirect(url_for('contact'))

    return render_template("contact.html")

def send_email_notification(name, email, message):
    sender_email = os.getenv("SENDER_EMAIL")
    receiver_email = os.getenv("RECEIVER_EMAIL")
    password = os.getenv("EMAIL_PASSWORD")

    subject = "New Contact Form Submission"
    body = f"Name: {name}\nEmail: {email}\nMessage:\n{message}"

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = receiver_email

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
    except Exception as e:
        print("Database or email error:", e)

if __name__ == "__main__":
    app.run(debug=True)
