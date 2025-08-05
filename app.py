from flask import Flask, render_template, request, send_file, redirect, url_for
import os

app = Flask(__name__)
DOWNLOAD_PATH = os.path.join("static", "sample.docx")
COUNTER_FILE = "download_count.txt"

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        return redirect(url_for("result"))
    return render_template("index.html")

@app.route("/result")
def result():
    return render_template("result.html")

@app.route("/download/<filename>")
def download(filename):
    # Đếm lượt tải
    if os.path.exists(COUNTER_FILE):
        with open(COUNTER_FILE, "r+") as f:
            count = int(f.read().strip())
            f.seek(0)
            f.write(str(count + 1))
            f.truncate()
    return send_file(os.path.join("static", filename), as_attachment=True)

@app.route("/download-count")
def download_count():
    if os.path.exists(COUNTER_FILE):
        with open(COUNTER_FILE, "r") as f:
            return f"Đã có {f.read().strip()} lượt tải về."
    return "0"

if __name__ == "__main__":
    app.run(debug=True)