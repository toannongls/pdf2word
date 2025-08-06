import os
import logging
from flask import Flask, request, render_template, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from pdf2docx import parse
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

# Hàm để chuyển đổi PDF sang Word sử dụng pdf2docx
# LƯU Ý: Thư viện pdf2docx có khả năng giữ định dạng tốt hơn
# pdfminer.six và python-docx, đặc biệt với bảng và hình ảnh.
# Tuy nhiên, nó vẫn có giới hạn và không đảm bảo giữ nguyên 100% định dạng
# cho tất cả các loại PDF phức tạp (ví dụ: bố cục phức tạp, font nhúng đặc biệt).
def pdf_to_word_convert(pdf_path, docx_path):
    """
    Chuyển đổi file PDF sang định dạng Word (.docx) sử dụng thư viện pdf2docx.
    Cố gắng giữ nguyên định dạng tốt hơn so với phương pháp trích xuất văn bản thô.
    """
    try:
        logging.info(f"Bắt đầu chuyển đổi PDF sang Word bằng pdf2docx: {pdf_path}")
        parse(pdf_path, docx_path)
        logging.info("Chuyển đổi thành công bằng pdf2docx.")
        return True
    except Exception as e:
        logging.error(f"Lỗi khi chuyển đổi PDF sang Word cho {pdf_path} bằng pdf2docx: {e}", exc_info=True)
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

    # Server-side file type validation
    if not file.filename.lower().endswith('.pdf'):
        logging.warning(f"Tệp không phải PDF: {file.filename}")
        return jsonify({'error': 'Tệp đã chọn không phải là PDF. Vui lòng chọn tệp PDF.'}), 400

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
            
            # Gọi hàm chuyển đổi mới sử dụng pdf2docx
            if pdf_to_word_convert(pdf_path, docx_path):
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
            # Lưu ý về việc dọn dẹp file DOCX đã chuyển đổi:
            # Trên các nền tảng như Render, hệ thống file là ephemeral (tạm thời).
            # Các file trong thư mục 'converted' sẽ bị xóa khi container khởi động lại.
            # Đối với một ứng dụng đơn giản, việc không tự động xóa file DOCX ngay lập tức
            # sau khi chuyển đổi là chấp nhận được để người dùng có thời gian tải xuống.
            # Nếu cần dọn dẹp chủ động hơn, sẽ cần một cơ chế background task phức tạp hơn.

@app.route('/download/<filename>')
def download_file(filename):
    """
    Cho phép người dùng tải về file đã chuyển đổi.
    """
    logging.info(f"Yêu cầu tải file: {filename}")
    try:
        # Sử dụng send_from_directory để phục vụ file một cách an toàn
        response = send_from_directory(app.config['CONVERTED_FOLDER'], filename, as_attachment=True)
        # Tùy chọn: Xóa file sau khi đã gửi thành công
        # Đây là một cách để dọn dẹp, nhưng có thể gây lỗi nếu người dùng tải lại trang
        # hoặc có nhiều yêu cầu tải cùng lúc. Cần cân nhắc kỹ.
        # @response.call_on_close
        # def cleanup_file():
        #     file_to_delete = os.path.join(app.config['CONVERTED_FOLDER'], filename)
        #     if os.path.exists(file_to_delete):
        #         try:
        #             os.remove(file_to_delete)
        #             logging.info(f"Đã xóa file DOCX sau khi tải xuống: {file_to_delete}")
        #         except Exception as e:
        #             logging.error(f"Lỗi khi xóa file DOCX sau tải xuống {file_to_delete}: {e}", exc_info=True)
        return response
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
