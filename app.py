# app.py
from flask import Flask, render_template, request, send_from_directory, redirect, url_for, flash, session
import os
import pytesseract
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
from pdf2image import convert_from_path
from docx import Document
from werkzeug.utils import secure_filename
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "your_secret_key"

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
DB_PATH = "downloads.db"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["OUTPUT_FOLDER"] = OUTPUT_FOLDER

# Đúng cú pháp cho Flask-Limiter phiên bản mới
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["5 per minute"]
)
limiter.init_app(app)

# DB setup
with sqlite3.connect(DB_PATH) as db:
    db.execute("""
        CREATE TABLE IF NOT EXISTS downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            ip TEXT,
            timestamp TEXT
        )
    """)

def pdf_to_text(pdf_path):
    try:
        images = convert_from_path(pdf_path)
        text = ""
        for img in images:
            text += pytesseract.image_to_string(img, lang="vie") + "\n"
        return text
    except Exception as e:
        print(f"[ERROR] convert_from_path failed: {e}")
        return None

def save_to_word(text, output_path):
    doc = Document()
    doc.add_paragraph(text)
    doc.save(output_path)

def log_download(filename, ip):
    with sqlite3.connect(DB_PATH) as db:
        db.execute("INSERT INTO downloads (filename, ip, timestamp) VALUES (?, ?, ?)",
                   (filename, ip, datetime.utcnow().isoformat()))

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        file = request.files.get("pdf_file")
        if file and file.filename.endswith(".pdf"):
            filename = secure_filename(file.filename)
            input_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(input_path)

            output_filename = filename.rsplit(".", 1)[0] + ".docx"
            output_path = os.path.join(app.config["OUTPUT_FOLDER"], output_filename)

            text = pdf_to_text(input_path)
            if text is None:
                flash("Chuyển đổi PDF thất bại. Kiểm tra định dạng file hoặc cấu hình server.")
                return redirect(url_for("index"))

            save_to_word(text, output_path)

            session["converted_file"] = output_filename
            session["download_clicked"] = False

            return render_template("index.html", show_download=True, filename=output_filename)
        else:
            flash("Vui lòng tải lên file PDF hợp lệ.")
            return redirect(url_for("index"))

    return render_template("index.html")

@app.route("/download-ad")
def download_ad():
    if "converted_file" not in session:
        return redirect(url_for("index"))

    if not session.get("download_clicked"):
        session["download_clicked"] = True
        return render_template("ad_redirect.html", filename=session["converted_file"])
    else:
        filename = session.pop("converted_file", None)
        session.pop("download_clicked", None)
        log_download(filename, request.remote_addr)
        return send_from_directory(app.config["OUTPUT_FOLDER"], filename, as_attachment=True)

# Gunicorn entry point
# Content omitted for brevity