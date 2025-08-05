# app.py
from flask import Flask, render_template, request, send_from_directory, redirect, url_for
import os
import pytesseract
from pdf2image import convert_from_path
from docx import Document
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["OUTPUT_FOLDER"] = OUTPUT_FOLDER

# OCR + Save to Word
def pdf_to_text(pdf_path):
    images = convert_from_path(pdf_path)
    text = ""
    for img in images:
        text += pytesseract.image_to_string(img, lang="vie") + "\n"
    return text

def save_to_word(text, output_path):
    doc = Document()
    doc.add_paragraph(text)
    doc.save(output_path)

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
            save_to_word(text, output_path)

            return render_template("index.html", download_link=url_for("download_file", filename=output_filename))
    return render_template("index.html")

@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(app.config["OUTPUT_FOLDER"], filename, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
