from flask import Flask, request, send_file, session, redirect, url_for, render_template
import requests
import sqlite3
import random
import string
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import qrcode
from PIL import Image
from pyzbar.pyzbar import decode

app = Flask(__name__)
app.secret_key = "supersecretkey123"  # Change in production

OCR_API_KEY = "K89542782088957"  # Replace with your OCR.Space API key
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
    meds_str = ','.join(medications)
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
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def role_required(role):
    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'role' not in session or session['role'] != role:
                return "Access denied for your role."
            return f(*args, **kwargs)
        return decorated
    return wrapper

# -------------------
# Routes
# -------------------

@app.route('/')
def home():
    return render_template('home.html', username=session.get('username'), role=session.get('role'))

# -------------------
# Signup/Login (No verification)
# -------------------

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        name = request.form['name']
        license_id = request.form['license_id']
        organization = request.form['organization']

        hashed_pw = generate_password_hash(password)
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        try:
            c.execute('''
                INSERT INTO users (username, password, role, name, license_id, organization)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (username, hashed_pw, role, name, license_id, organization))
            conn.commit()
        except sqlite3.IntegrityError:
            return "Username already exists"
        conn.close()
        message = "Signup successful! You can now login."
        return render_template('message.html', title='Signup Successful', message=message, link_url=url_for('login'), link_text='Login')
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT id, password, role FROM users WHERE username=?", (username,))
        user = c.fetchone()
        conn.close()
        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            session['role'] = user[2]
            session['username'] = username
            return redirect(url_for('home'))
        else:
            message = "Invalid username or password."
            return render_template('message.html', title='Login Failed', message=message, link_url=url_for('login'), link_text='Try Again')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# -------------------
# Issuer: Create Prescription
# -------------------
@app.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('issuer')
def create():
    if request.method == 'POST':
        doctor_name = request.form['doctor_name']
        doctor_id = request.form['doctor_id']
        patient_name = request.form['patient_name']
        date = request.form['date']
        medications = request.form['medications'].split(',')
        code = generate_code()
        add_prescription(code, doctor_name, doctor_id, patient_name, date, medications)
        return render_template('created.html', code=code)

    return render_template('create.html')

# -------------------
# Verifier: Combined Verify (Image + Code)
# -------------------
@app.route('/verify', methods=['GET', 'POST'])
@login_required
@role_required('verifier')
def verify():
    if request.method == 'POST':
        code = None
        # Check if file uploaded
        file = request.files.get('prescription')
        if file and file.filename != '':
            fname = file.filename.lower()
            # Handle PDF uploads
            if fname.endswith('.pdf') or file.mimetype == 'application/pdf':
                # read bytes once
                file_bytes = file.read()

                # 1) Try to extract text from PDF using PyPDF2 (if installed)
                extracted_text = ''
                try:
                    from PyPDF2 import PdfReader
                    reader = PdfReader(BytesIO(file_bytes))
                    for page in reader.pages:
                        try:
                            extracted_text += (page.extract_text() or '') + "\n"
                        except Exception:
                            # continue if a page fails
                            continue
                except Exception:
                    extracted_text = ''

                if extracted_text:
                    for line in extracted_text.splitlines():
                        if "Prescription Code" in line or "Code" in line:
                            code = line.split(":")[-1].strip()
                            break

                # 2) If no code yet, try to decode QR from first PDF page using pdf2image (if available)
                if not code:
                    try:
                        from pdf2image import convert_from_bytes
                        images = convert_from_bytes(file_bytes)
                        if images:
                            qr_data = decode(images[0])
                            if qr_data:
                                code = qr_data[0].data.decode('utf-8')
                    except Exception:
                        # pdf2image not available or conversion failed, continue
                        pass

                # 3) Fallback to OCR.Space for PDF if still no code
                if not code:
                    try:
                        response = requests.post(
                            "https://api.ocr.space/parse/image",
                            files={"filename": ("prescription.pdf", file_bytes)},
                            data={"apikey": OCR_API_KEY, "language": "eng"}
                        )
                        result = response.json()
                        parsed_results = result.get("ParsedResults")
                        if parsed_results:
                            text = parsed_results[0].get("ParsedText", "")
                            for line in text.split("\n"):
                                if "Prescription Code" in line or "Code" in line:
                                    code = line.split(":")[-1].strip()
                                    break
                    except Exception:
                        # network/OCR failure - leave code as None
                        pass
            else:
                # treat as image
                try:
                    file.seek(0)
                    img = Image.open(file)
                    qr_data = decode(img)
                    if qr_data:
                        code = qr_data[0].data.decode('utf-8')
                    else:
                        # fallback to OCR
                        file.seek(0)
                        file_bytes = file.read()
                        response = requests.post(
                            "https://api.ocr.space/parse/image",
                            files={"filename": ("prescription.png", file_bytes)},
                            data={"apikey": OCR_API_KEY, "language": "eng"}
                        )
                        result = response.json()
                        parsed_results = result.get("ParsedResults")
                        if parsed_results:
                            text = parsed_results[0].get("ParsedText", "")
                            for line in text.split("\n"):
                                if "Prescription Code" in line or "Code" in line:
                                    code = line.split(":")[-1].strip()
                                    break
                except Exception:
                    # Image open/QR decode failed; try OCR as last resort
                    try:
                        file.seek(0)
                        file_bytes = file.read()
                        response = requests.post(
                            "https://api.ocr.space/parse/image",
                            files={"filename": ("prescription.png", file_bytes)},
                            data={"apikey": OCR_API_KEY, "language": "eng"}
                        )
                        result = response.json()
                        parsed_results = result.get("ParsedResults")
                        if parsed_results:
                            text = parsed_results[0].get("ParsedText", "")
                            for line in text.split("\n"):
                                if "Prescription Code" in line or "Code" in line:
                                    code = line.split(":")[-1].strip()
                                    break
                    except Exception:
                        pass

        # If code entered manually
        if not code:
            code = request.form.get('code', '').strip()

        if not code:
            return "Cannot detect prescription code. Please upload an image or enter a code."

        db_entry = get_prescription(code)
        if not db_entry:
            return f"Prescription code {code} NOT found in database."

        # Extract fields and render result (inside POST branch so db_entry always defined)
        doctor_name, doctor_id, patient_name, date, medications = db_entry[1], db_entry[2], db_entry[3], db_entry[4], db_entry[5].split(',')
        return render_template('verify_result.html', code=code, doctor_name=doctor_name, doctor_id=doctor_id, patient_name=patient_name, date=date, medications=medications)

    # GET -> show verify form
    return render_template('verify.html')

# -------------------
# Download PDF with QR
# -------------------
@app.route('/download/<code>')
@login_required
def download_prescription(code):
    db_entry = get_prescription(code)
    if not db_entry:
        return f"Prescription code {code} NOT found."

    doctor_name, doctor_id, patient_name, date, medications = db_entry[1], db_entry[2], db_entry[3], db_entry[4], db_entry[5].split(',')

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    y = height - 50
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Prescription")
    y -= 40

    c.setFont("Helvetica", 12)
    c.drawString(50, y, f"Prescription Code: {code}")
    y -= 20
    c.drawString(50, y, f"Doctor Name: {doctor_name}")
    y -= 20
    c.drawString(50, y, f"Doctor ID: {doctor_id}")
    y -= 20
    c.drawString(50, y, f"Patient Name: {patient_name}")
    y -= 20
    c.drawString(50, y, f"Date: {date}")
    y -= 30

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Medications (with Quantity):")
    y -= 20
    c.setFont("Helvetica", 12)
    for med in medications:
        c.drawString(60, y, f"- {med.strip()}")
        y -= 20

    # QR code
    qr_data = f"{code}"
    qr = qrcode.QRCode(box_size=2, border=1)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    c.drawInlineImage(img, 400, height - 150)

    c.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"Prescription_{code}.pdf", mimetype='application/pdf')


# -------------------
# Run App
# -------------------
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
