from flask import Flask, request, send_file, session, redirect, url_for, jsonify
import requests
import sqlite3
import random
import string
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import qrcode
from PIL import Image
import PyPDF2
from pyzbar.pyzbar import decode
import os

app = Flask(__name__)
app.secret_key = "supersecretkey123"  # Change in production

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

OCR_API_KEY = os.getenv("OCR_API_KEY")
if not OCR_API_KEY:
    print("Warning: OCR_API_KEY not set. OCR features will not work.")

DB_FILE = "prescriptions.db"

# -------------------
# Helper Functions
# -------------------

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS prescriptions (
            code TEXT PRIMARY KEY,
            doctor_name TEXT,
            doctor_id TEXT,
            patient_name TEXT,
            date TEXT,
            medications TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT,
            name TEXT,
            license_id TEXT,
            organization TEXT
        )
    ''')
    conn.commit()
    conn.close()

def generate_code(length=8):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def add_prescription(code, doctor_name, doctor_id, patient_name, date, medications):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    meds_str = ','.join(medications) if isinstance(medications, list) else medications
    c.execute('''
        INSERT INTO prescriptions (code, doctor_name, doctor_id, patient_name, date, medications)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (code, doctor_name, doctor_id, patient_name, date, meds_str))
    conn.commit()
    conn.close()

def get_prescription(code):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM prescriptions WHERE code=?", (code,))
    result = c.fetchone()
    conn.close()
    return result

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return "Please login first", 401
        return f(*args, **kwargs)
    return decorated

def role_required(role):
    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'role' not in session or session['role'] != role:
                return "Access denied for your role.", 403
            return f(*args, **kwargs)
        return decorated
    return wrapper

def extract_code_from_pdf(pdf_file):
    """Extract QR code or text code from PDF"""
    try:
        # Try to extract images and decode QR codes
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        # Try to extract text first
        for page in pdf_reader.pages:
            text = page.extract_text()
            # Look for prescription code pattern
            import re
            matches = re.findall(r'Code:\s*([A-Z0-9]{8})', text)
            if matches:
                return matches[0]
            
            # Also try direct pattern match
            matches = re.findall(r'\b([A-Z0-9]{8})\b', text)
            if matches:
                return matches[0]
        
        # If text extraction fails, try to extract images for QR codes
        pdf_file.seek(0)
        # Convert first page to image and try QR detection
        # This requires pdf2image library which you may need to install
        
    except Exception as e:
        print(f"PDF extraction error: {e}")
    
    return None

# -------------------
# Routes
# -------------------

@app.route('/')
def home():
    return send_file('static/index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return send_file('static/index.html')
        
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role', 'issuer')
    name = request.form.get('name', '')
    license_id = request.form.get('license_id', '')
    organization = request.form.get('organization', '')

    hashed_pw = generate_password_hash(password)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO users (username, password, role, name, license_id, organization)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, hashed_pw, role, name, license_id, organization))
        conn.commit()
        conn.close()
        
        if request.headers.get('Accept') == 'application/json':
            return jsonify({"message": "Signup successful!"}), 200
        return redirect(url_for('home'))
        
    except sqlite3.IntegrityError:
        conn.close()
        error = "Username already exists"
        if request.headers.get('Accept') == 'application/json':
            return jsonify({"error": error}), 400
        return f'<script>alert("{error}"); window.location="/";</script>'

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, password, role FROM users WHERE username=?", (username,))
    user = c.fetchone()
    conn.close()
    
    if user and check_password_hash(user[1], password):
        session['user_id'] = user[0]
        session['role'] = user[2]
        session['username'] = username
        return f"Login successful! Role: {user[2]}", 200
    else:
        return "Invalid username or password", 401

@app.route('/logout')
def logout():
    session.clear()
    return "Logged out successfully", 200

# -------------------
# Create Prescription (Issuer)
# -------------------
@app.route('/create', methods=['POST'])
def create():
    # For now, allow without login for testing
    # Uncomment these decorators in production:
    # @login_required
    # @role_required('issuer')
    
    doctor_name = request.form.get('doctor_name')
    doctor_id = request.form.get('doctor_id')
    patient_name = request.form.get('patient_name')
    date = request.form.get('date')
    medications = request.form.get('medications', '')
    
    code = generate_code()
    add_prescription(code, doctor_name, doctor_id, patient_name, date, medications)
    
    return f"Prescription Created Successfully!\n\nCode: {code}\n\nClick the download button to get your PDF.", 200

# -------------------
# Verify Prescription (Verifier)
# -------------------
@app.route('/verify', methods=['POST'])
def verify():
    # For now, allow without login for testing
    code = None
    
    # Check if file was uploaded
    file = request.files.get('prescription')
    if file and file.filename:
        try:
            # Check if it's a PDF
            if file.filename.lower().endswith('.pdf'):
                code = extract_code_from_pdf(file)
            else:
                # It's an image, try QR decode
                img = Image.open(file)
                qr_data = decode(img)
                
                if qr_data:
                    code = qr_data[0].data.decode('utf-8')
                else:
                    # Fallback to OCR if available
                    if OCR_API_KEY:
                        file.seek(0)
                        file_bytes = file.read()
                        response = requests.post(
                            "https://api.ocr.space/parse/image",
                            files={"filename": (file.filename, file_bytes)},
                            data={"apikey": OCR_API_KEY, "language": "eng"}
                        )
                        result = response.json()
                        parsed_results = result.get("ParsedResults")
                        if parsed_results:
                            text = parsed_results[0].get("ParsedText", "")
                            import re
                            matches = re.findall(r'\b([A-Z0-9]{8})\b', text)
                            if matches:
                                code = matches[0]
        except Exception as e:
            return f"Error processing file: {str(e)}", 400
    
    # If code field is filled, use it (overrides file upload)
    form_code = request.form.get('code', '').strip()
    if form_code:
        code = form_code
    
    if not code:
        return "Cannot detect prescription code. Please upload a valid PDF/image or enter a code manually.", 400
    
    # Look up in database
    db_entry = get_prescription(code)
    if not db_entry:
        return f"❌ Prescription code {code} NOT found in database.\n\nThis prescription may be invalid or has not been issued.", 404
    
    # Extract details
    _, doctor_name, doctor_id, patient_name, date, medications = db_entry
    meds_list = medications.split(',')
    
    # Format response as HTML
    response_html = f"""
    <h3 style="color: #065f46; margin-bottom: 16px;">✓ Prescription Verified Successfully</h3>
    <div style="background: white; padding: 16px; border-radius: 8px; border: 2px solid #6ee7b7;">
        <p style="margin: 8px 0;"><strong>Code:</strong> {code}</p>
        <p style="margin: 8px 0;"><strong>Doctor Name:</strong> {doctor_name}</p>
        <p style="margin: 8px 0;"><strong>Doctor ID:</strong> {doctor_id}</p>
        <p style="margin: 8px 0;"><strong>Patient Name:</strong> {patient_name}</p>
        <p style="margin: 8px 0;"><strong>Date:</strong> {date}</p>
        <p style="margin: 8px 0;"><strong>Medications:</strong></p>
        <ul style="margin: 8px 0; padding-left: 20px;">
            {''.join([f'<li>{med.strip()}</li>' for med in meds_list])}
        </ul>
    </div>
    """
    
    return response_html, 200

# -------------------
# Download PDF with QR Code
# -------------------
@app.route('/download/<code>')
def download_prescription(code):
    db_entry = get_prescription(code)
    if not db_entry:
        return f"Prescription code {code} NOT found.", 404
    
    _, doctor_name, doctor_id, patient_name, date, medications = db_entry
    meds_list = medications.split(',')
    
    # Create PDF
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Header with gradient effect (using colors)
    c.setFillColorRGB(0.4, 0.49, 0.92)  # Purple color
    c.rect(0, height - 100, width, 100, fill=1, stroke=0)
    
    # Title
    c.setFillColorRGB(1, 1, 1)  # White text
    c.setFont("Helvetica-Bold", 28)
    c.drawString(50, height - 60, "🏥 Medical Prescription")
    
    # Reset to black for body
    c.setFillColorRGB(0, 0, 0)
    
    # Prescription details
    y = height - 140
    
    # Code in a box
    c.setFillColorRGB(0.95, 0.95, 0.98)
    c.rect(40, y - 30, 250, 40, fill=1, stroke=1)
    c.setFillColorRGB(0.4, 0.49, 0.92)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y - 10, "Prescription Code:")
    c.setFont("Helvetica-Bold", 18)
    c.drawString(200, y - 10, code)
    
    y -= 70
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Doctor Information:")
    c.setFont("Helvetica", 11)
    y -= 20
    c.drawString(60, y, f"Name: {doctor_name}")
    y -= 18
    c.drawString(60, y, f"License ID: {doctor_id}")
    
    y -= 35
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Patient Information:")
    c.setFont("Helvetica", 11)
    y -= 20
    c.drawString(60, y, f"Name: {patient_name}")
    y -= 18
    c.drawString(60, y, f"Date: {date}")
    
    y -= 35
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Prescribed Medications:")
    c.setFont("Helvetica", 11)
    y -= 20
    
    for med in meds_list:
        c.drawString(60, y, f"• {med.strip()}")
        y -= 18
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(code)
    qr.make(fit=True)
    
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)
    
    # Draw QR code
    qr_reader = ImageReader(qr_buffer)
    c.drawImage(qr_reader, width - 200, height - 280, width=150, height=150)
    
    # Add QR code label
    c.setFont("Helvetica-Bold", 10)
    c.drawString(width - 190, height - 295, "Scan to Verify")
    
    # Footer
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawString(50, 30, "This is a digitally generated prescription. Verify authenticity using the QR code or prescription code.")
    c.drawString(50, 20, f"Generated by RxVerify System • Code: {code}")
    
    c.save()
    buffer.seek(0)
    
    return send_file(
        buffer, 
        as_attachment=True, 
        download_name=f"Prescription_{code}.pdf", 
        mimetype='application/pdf'
    )

# -------------------
# Static file serving (for UI)
# -------------------
@app.route('/static/<path:path>')
def send_static(path):
    return send_file(f'static/{path}')

# -------------------
# Run App
# -------------------
if __name__ == '__main__':
    init_db()
    print("=" * 50)
    print("RxVerify System Starting...")
    print("=" * 50)
    print("\nDatabase initialized successfully!")
    print("\nAccess the application at: http://localhost:5000")
    print("\nNote: For production, ensure you:")
    print("  1. Change the secret_key")
    print("  2. Set OCR_API_KEY environment variable")
    print("  3. Enable login_required decorators")
    print("=" * 50)
    app.run(debug=True, port=5000)