from flask import Flask, render_template, request, send_from_directory, redirect, url_for, flash, session, g
import os
import pytesseract
from pdf2image import convert_from_path
from docx import Document
from werkzeug.utils import secure_filename
import sqlite3
from datetime import datetime
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# configure tesseract path if needed (inside Docker it is /usr/bin/tesseract)
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

app = Flask(__name__)
app.secret_key = "your_secret_key"

# rate limiter
limiter = Limiter(app, key_func=get_remote_address, default_limits=["5 per minute"])

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
DB_PATH = "metrics.db"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["OUTPUT_FOLDER"] = OUTPUT_FOLDER

def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH, check_same_thread=False)
        db.execute("""
        CREATE TABLE IF NOT EXISTS downloads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        ip TEXT,
        timestamp TEXT
        )""")
        db.execute("""
        CREATE TABLE IF NOT EXISTS conversions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            ip TEXT,
            timestamp TEXT
        )""")
        db.commit()
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db:
        db.close()

def record_conversion(filename):
    db = get_db()
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    db.execute("INSERT INTO conversions (filename, ip, timestamp) VALUES (?, ?, ?)",
               (filename, ip, datetime.utcnow().isoformat()))
    db.commit()

def record_download(filename):
    db = get_db()
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    db.execute("INSERT INTO downloads (filename, ip, timestamp) VALUES (?, ?, ?)",
               (filename, ip, datetime.utcnow().isoformat()))
    db.commit()

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

@app.route("/", methods=["GET", "POST"])
@limiter.limit("3 per 2 minutes")
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
                flash("Chuyển đổi PDF thất bại. Vui lòng thử lại hoặc kiểm tra file.") 
                return redirect(url_for("index"))

            save_to_word(text, output_path)
            record_conversion(output_filename)

            session["converted_file"] = output_filename
            session["download_clicked"] = False

            return render_template("index.html", show_download=True, filename=output_filename)
        else:
            flash("Vui lòng tải lên file PDF hợp lệ.")
            return redirect(url_for("index"))
    return render_template("index.html")

@app.route("/download-ad")
@limiter.limit("10 per minute")
def download_ad():
    if "converted_file" not in session:
        return redirect(url_for("index"))

    if not session.get("download_clicked"):
        session["download_clicked"] = True
        return render_template("ad_redirect.html", filename=session["converted_file"])
    else:
        filename = session.pop("converted_file", None)
        session.pop("download_clicked", None)
        if filename:
            record_download(filename)
            return send_from_directory(app.config["OUTPUT_FOLDER"], filename, as_attachment=True)
        return redirect(url_for("index"))

@app.route("/stats")
def stats():
    db = get_db()
    cur = db.execute("SELECT filename, COUNT(*) as cnt FROM downloads GROUP BY filename")
    downloads = [{"file": r[0], "count": r[1]} for r in cur.fetchall()]
    cur2 = db.execute("SELECT filename, COUNT(*) as cnt FROM conversions GROUP BY filename")
    conversions = [{"file": r[0], "count": r[1]} for r in cur2.fetchall()]
    return {"downloads": downloads, "conversions": conversions}