from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import uuid
from ocr_engine import process_prescription

app = Flask(__name__)

# Allow your MedVault frontend to call this API
CORS(app, origins=["*"])

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'bmp', 'tiff', 'webp'}
MAX_FILE_SIZE_MB = 10

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE_MB * 1024 * 1024

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ─────────────────────────────────────────
# ROUTE 1: Health check
# GET /
# ─────────────────────────────────────────
@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "MedVault OCR API is running",
        "version": "1.0.0",
        "endpoints": {
            "extract": "POST /extract-medicines",
            "health":  "GET /health"
        }
    })

# ─────────────────────────────────────────
# ROUTE 2: Health ping
# GET /health
# ─────────────────────────────────────────
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

# ─────────────────────────────────────────
# ROUTE 3: Main OCR endpoint
# POST /extract-medicines
# Body: multipart/form-data with key "file"
# Returns: { medicines: [...], raw_text: "...", total_found: N }
# ─────────────────────────────────────────
@app.route('/extract-medicines', methods=['POST'])
def extract_medicines():

    # Check file exists in request
    if 'file' not in request.files:
        return jsonify({"error": "No file provided. Send file with key 'file'"}), 400

    file = request.files['file']

    # Check file was actually selected
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    # Check file type
    if not allowed_file(file.filename):
        return jsonify({
            "error": f"File type not supported. Allowed: {ALLOWED_EXTENSIONS}"
        }), 400

    # Save file with unique name to avoid conflicts
    ext = file.filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(file_path)

    try:
        # Run OCR
        result = process_prescription(file_path)
        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        # Always delete the uploaded file after processing
        if os.path.exists(file_path):
            os.remove(file_path)

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    print("🚀 MedVault OCR API starting on http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)