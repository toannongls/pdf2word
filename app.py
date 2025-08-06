from flask import Flask, render_template, request, send_from_directory, redirect, url_for, flash, session
import os
from werkzeug.utils import secure_filename
from pdf2docx import Converter

app = Flask(__name__)
app.secret_key = "your_secret_key"

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["OUTPUT_FOLDER"] = OUTPUT_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB limit

# Chuyển đổi PDF sang DOCX (không dùng OCR)
def convert_pdf_to_docx(pdf_path, docx_path):
    try:
        cv = Converter(pdf_path)
        cv.convert(docx_path, start=0, end=None)
        cv.close()
        return True
    except Exception as e:
        print(f"[ERROR] PDF conversion failed: {e}")
        return False

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

            success = convert_pdf_to_docx(input_path, output_path)
            if not success:
                flash("Chuyển đổi PDF thất bại. Kiểm tra định dạng file hoặc cấu hình server.")
                return redirect(url_for("index"))

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
        # Lần đầu click: mở quảng cáo
        session["download_clicked"] = True
        return render_template("ad_redirect.html", filename=session["converted_file"])
    else:
        filename = session.pop("converted_file", None)
        session.pop("download_clicked", None)
        return send_from_directory(app.config["OUTPUT_FOLDER"], filename, as_attachment=True)

# Gunicorn sẽ tự động tìm app này để chạy
