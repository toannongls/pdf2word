# Dựa trên image Python nhẹ
FROM python:3.10-slim

# Cài đặt các gói cần thiết
RUN apt-get update && \
    apt-get install -y \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-vie \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Thiết lập thư mục làm việc
WORKDIR /app

# Sao chép file requirements và cài thư viện Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép mã nguồn còn lại
COPY . .

# Chạy ứng dụng Flask
CMD ["python", "app.py"]
