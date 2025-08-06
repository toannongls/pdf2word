import os
import logging
from flask import Flask, request, render_template, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from pdfminer.high_level import extract_text
from docx import Document
from docx.shared import Inches
import re

# Cấu hình logging cơ bản
# Điều này giúp bạn theo dõi các hoạt động và lỗi trên môi trường online
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Cấu hình thư mục lưu trữ file tạm thời
# Đảm bảo các thư mục này tồn tại và có quyền ghi
UPLOAD_FOLDER = 'uploads'
CONVERTED_FOLDER = 'converted'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CONVERTED_FOLDER'] = CONVERTED_FOLDER

# Tạo thư mục nếu chưa tồn tại
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)

# Hàm đơn giản để chuyển đổi PDF sang Word
# LƯU Ý QUAN TRỌNG: Hàm này chủ yếu trích xuất VĂN BẢN thô từ PDF.
# Nó KHÔNG thể giữ nguyên định dạng phức tạp như bảng biểu, hình ảnh,
# bố cục nhiều cột, font chữ, màu sắc, hoặc các yếu tố đồ họa.
# Để giữ định dạng tốt hơn, cần sử dụng các thư viện hoặc API thương mại chuyên dụng.
def pdf_to_word_simple(pdf_path, docx_path):
    """
    Trích xuất văn bản từ file PDF và lưu vào định dạng Word (.docx).
    Đây là một phương pháp đơn giản, có thể không giữ nguyên định dạng phức tạp.
    """
    try:
        logging.info(f"Bắt đầu trích xuất văn bản từ PDF: {pdf_path}")
        text = extract_text(pdf_path)
        logging.info("Trích xuất văn bản thành công.")

        document = Document()
        
        # Chia văn bản thành các đoạn dựa trên dòng mới kép để giữ cấu trúc tốt hơn
        # Tuy nhiên, điều này không đảm bảo giữ nguyên định dạng phức tạp của PDF.
        paragraphs = text.split('\n\n')
        for para_text in paragraphs:
            cleaned_text = para_text.strip()
            if cleaned_text:
                document.add_paragraph(cleaned_text)
        
        logging.info(f"Lưu tài liệu Word vào: {docx_path}")
        document.save(docx_path)
        logging.info("Lưu tài liệu Word thành công.")
        return True
    except Exception as e:
        logging.error(f"Lỗi khi chuyển đổi PDF sang Word cho {pdf_path}: {e}", exc_info=True)
        return False

@app.route('/')
def index():
    """
    Hiển thị trang chủ với form tải lên.
    """
    logging.info("Truy cập trang chủ.")
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert_pdf():
    """
    Xử lý yêu cầu chuyển đổi PDF.
    - Nhận file PDF từ người dùng.
    - Lưu file tạm thời.
    - Chuyển đổi sang Word.
    - Trả về đường dẫn tải về.
    """
    logging.info("Nhận yêu cầu chuyển đổi PDF.")
    if 'pdf_file' not in request.files:
        logging.warning("Không có tệp nào được chọn trong yêu cầu.")
        return jsonify({'error': 'Không có tệp nào được chọn'}), 400

    file = request.files['pdf_file']
    if file.filename == '':
        logging.warning("Tên tệp trống.")
        return jsonify({'error': 'Không có tệp nào được chọn'}), 400

    if file:
        original_filename = secure_filename(file.filename)
        base_filename = os.path.splitext(original_filename)[0]
        
        # Đảm bảo tên file an toàn cho URL và hệ thống file
        safe_base_filename = re.sub(r'[^\w\s-]', '', base_filename).strip()
        safe_base_filename = re.sub(r'[-\s]+', '-', safe_base_filename)
        
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)
        docx_filename = f"{safe_base_filename}.docx"
        docx_path = os.path.join(app.config['CONVERTED_FOLDER'], docx_filename)

        try:
            logging.info(f"Lưu file PDF tải lên: {pdf_path}")
            file.save(pdf_path) # Lưu file PDF tải lên
            
            if pdf_to_word_simple(pdf_path, docx_path):
                logging.info(f"Chuyển đổi thành công, file Word: {docx_filename}")
                return jsonify({
                    'message': 'Chuyển đổi thành công!',
                    'download_filename': docx_filename
                }), 200
            else:
                logging.error(f"Chuyển đổi thất bại cho file: {original_filename}")
                return jsonify({'error': 'Không thể chuyển đổi tệp PDF. Vui lòng thử lại.'}), 500
        except Exception as e:
            logging.error(f"Lỗi xử lý file {original_filename}: {e}", exc_info=True)
            return jsonify({'error': f'Lỗi máy chủ nội bộ: {e}'}), 500
        finally:
            # Đảm bảo xóa file PDF đã tải lên sau khi xử lý để tránh tích tụ file
            if os.path.exists(pdf_path):
                try:
                    os.remove(pdf_path)
                    logging.info(f"Đã xóa file PDF tạm thời: {pdf_path}")
                except Exception as e:
                    logging.error(f"Lỗi khi xóa file PDF tạm thời {pdf_path}: {e}", exc_info=True)

@app.route('/download/<filename>')
def download_file(filename):
    """
    Cho phép người dùng tải về file đã chuyển đổi.
    """
    logging.info(f"Yêu cầu tải file: {filename}")
    try:
        # Sử dụng send_from_directory để phục vụ file một cách an toàn
        return send_from_directory(app.config['CONVERTED_FOLDER'], filename, as_attachment=True)
    except FileNotFoundError:
        logging.warning(f"Không tìm thấy tệp để tải xuống: {filename}")
        return jsonify({'error': 'Không tìm thấy tệp hoặc tệp đã bị xóa.'}), 404
    except Exception as e:
        logging.error(f"Lỗi khi tải file {filename}: {e}", exc_info=True)
        return jsonify({'error': 'Lỗi máy chủ khi tải xuống tệp.'}), 500

if __name__ == '__main__':
    # Khi triển khai trên Render, Gunicorn sẽ quản lý việc chạy ứng dụng.
    # Đoạn này chỉ chạy khi bạn chạy app.py trực tiếp để phát triển.
    logging.info("Ứng dụng Flask đang chạy ở chế độ phát triển.")
    app.run(debug=True, host='0.0.0.0', port=os.environ.get('PORT', 5000))

