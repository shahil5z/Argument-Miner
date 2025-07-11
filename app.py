import os
import queue
import threading
import time
from flask import Flask, request, render_template, jsonify, send_file
from werkzeug.utils import secure_filename
from groq import Groq
from PyPDF2 import PdfReader
from uuid import uuid4
from dotenv import load_dotenv
import io
import logging
from docx import Document

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(filename='app.log', level=logging.DEBUG, 
                    format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Project directories
BASE_DIR = r"C:\Users\SHAHIL\Downloads\PROJECT\Argument Miner"
OUTPUT_FOLDER = os.path.join(BASE_DIR, "saved.arg")
ALLOWED_EXTENSIONS = {'pdf'}

# Ensure output directory exists
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Configure GROQ API
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Queue for processing files
file_queue = queue.Queue()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(file_stream):
    try:
        logger.info("Extracting text from PDF")
        reader = PdfReader(file_stream)
        text = ""
        for page in reader.pages:
            extracted_text = page.extract_text()
            if extracted_text:
                text += extracted_text + "\n"
        if not text.strip():
            logger.warning("No text extracted from PDF")
            return None
        logger.info(f"Extracted {len(text)} characters from PDF")
        return text
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        return None
    finally:
        file_stream.seek(0)  # Reset stream position

def save_text_to_file(text, filename, file_format):
    try:
        output_filename = f"{os.path.splitext(filename)[0]}_extracted.{file_format}"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        if file_format == 'txt':
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text)
        elif file_format == 'doc':
            doc = Document()
            doc.add_paragraph(text)
            doc.save(output_path)
        logger.info(f"Saved output to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving file {output_path}: {str(e)}")
        return False

def process_file(filename, file_stream, file_format):
    try:
        logger.info(f"Processing file: {filename}")
        # Extract text from PDF
        text = extract_text_from_pdf(file_stream)
        if text is None:
            logger.error(f"No text extracted for {filename}")
            return False

        # Send to GROQ API
        logger.info("Sending text to Grok API")
        prompt = "Extract the main arguments and key points from this text. Keep it short and clear."
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text}
            ]
        )
        extracted_content = response.choices[0].message.content
        if not extracted_content.strip():
            logger.error(f"No content returned from Grok API for {filename}")
            return False

        # Save extracted content
        return save_text_to_file(extracted_content, filename, file_format)
    except Exception as e:
        logger.error(f"Error processing file {filename}: {str(e)}")
        return False
    finally:
        file_stream.close()

def background_worker():
    while True:
        try:
            filename, file_stream, file_format = file_queue.get()
            process_file(filename, file_stream, file_format)
            file_queue.task_done()
        except Exception as e:
            logger.error(f"Error in background worker: {str(e)}")
        time.sleep(1)

# Start background worker thread
threading.Thread(target=background_worker, daemon=True).start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            logger.error("No file part in request")
            return jsonify({'error': 'No file selected'}), 400
        file = request.files['file']
        file_format = request.form.get('file_format', 'txt')
        
        if file.filename == '':
            logger.error("No selected file")
            return jsonify({'error': 'No selected file'}), 400
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid4()}_{filename}"
            
            # Read file into memory
            file_stream = io.BytesIO(file.read())
            
            # Add to processing queue
            file_queue.put((unique_filename, file_stream, file_format))
            logger.info(f"Queued file {unique_filename} for processing")
            return jsonify({'message': 'File uploaded successfully, processing in background'}), 200
        logger.error(f"Invalid file type: {file.filename}")
        return jsonify({'error': 'Invalid file type. Only .pdf is allowed'}), 400
    except Exception as e:
        logger.error(f"Error in upload_file: {str(e)}")
        return jsonify({'error': 'An error occurred during upload'}), 500

@app.route('/files', methods=['GET'])
def list_files():
    try:
        files = [f for f in os.listdir(OUTPUT_FOLDER) if f.endswith(('.txt', '.doc', '.docx'))]
        logger.info(f"Listed {len(files)} files in {OUTPUT_FOLDER}")
        return render_template('files.html', files=files)
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        return render_template('files.html', files=[])

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    try:
        file_path = os.path.join(OUTPUT_FOLDER, filename)
        if os.path.exists(file_path):
            logger.info(f"Downloading file {filename}")
            return send_file(file_path, as_attachment=True)
        logger.error(f"File not found: {filename}")
        return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        logger.error(f"Error downloading file {filename}: {str(e)}")
        return jsonify({'error': 'File not found'}), 404

@app.route('/debug', methods=['GET'])
def debug():
    return jsonify({
        'static_css': os.path.exists(os.path.join(BASE_DIR, 'static', 'style.css')),
        'output_folder': os.path.exists(OUTPUT_FOLDER),
        'files_in_output': os.listdir(OUTPUT_FOLDER)
    })

if __name__ == '__main__':
    app.run(debug=True)