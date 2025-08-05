
from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename
import os
from pdf2docx import Converter

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    word_download_link = None
    if request.method == 'POST':
        file = request.files['pdf_file']
        if file and file.filename.endswith('.pdf'):
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)

            filename_wo_ext = os.path.splitext(filename)[0]
            output_path = f"{OUTPUT_FOLDER}/{filename_wo_ext}.docx"

            cv = Converter(filepath)
            cv.convert(output_path, start=0, end=None)
            cv.close()
            word_download_link = output_path
    return render_template('index.html', word_download_link=word_download_link)

@app.route('/output/<filename>')
def download_file(filename):
    return send_file(os.path.join(OUTPUT_FOLDER, filename), as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
