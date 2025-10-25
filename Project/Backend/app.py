from flask import Flask, request, send_file, session, redirect, url_for, render_template
import requests
import sqlite3
import random
import string
import os
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import qrcode
from PIL import Image
from pyzbar.pyzbar import decode
from hash_utils import generate_prescription_hash, verify_prescription_hash
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
OCR_API_KEY = os.getenv('OCR_API_KEY')

app = Flask(__name__)
app.secret_key = "supersecretkey123"  # Change in production

DB_FILE = "prescriptions.db"

# -------------------
# Helper Functions
# -------------------

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Backup existing prescriptions if table exists
    try:
        c.execute("SELECT * FROM prescriptions")
        existing_prescriptions = c.fetchall()
    except sqlite3.OperationalError:
        existing_prescriptions = []

    # Drop existing table
    c.execute("DROP TABLE IF EXISTS prescriptions")
    
    # Create new table with hash column
    c.execute('''
        CREATE TABLE prescriptions (
            code TEXT PRIMARY KEY,
            doctor_name TEXT,
            doctor_id TEXT,
            patient_name TEXT,
            date TEXT,
            medications TEXT,
            hash TEXT,
            previous_hash TEXT
        )
    ''')
    
    # Restore existing data with hash generation
    for prescription in existing_prescriptions:
        prescription_data = {
            'code': prescription[0],
            'doctor_name': prescription[1],
            'doctor_id': prescription[2],
            'patient_name': prescription[3],
            'date': prescription[4],
            'medications': prescription[5].split(',')
        }
        prescription_hash = generate_prescription_hash(prescription_data)
        c.execute('''
            INSERT INTO prescriptions (code, doctor_name, doctor_id, patient_name, date, medications, hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (prescription[0], prescription[1], prescription[2], prescription[3], prescription[4], prescription[5], prescription_hash))
    
    # Create users table
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

def get_previous_code():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        
        # Backup existing prescriptions if table exists
        try:
            c.execute("SELECT hash FROM prescriptions ORDER BY id DESC LIMIT 1;")
            result = c.fetchone()

            if result:
                return result[0]
            else:
                return ''
        except Exception as e:
            print(f"CRITICAL ERROR: An unexpected error occurred: {e}")
            return ''

def add_prescription(code, previous_code, doctor_name, doctor_id, patient_name, date, medications):
    # Create prescription data for hashing
    prescription_data = {
        'code': code,
        'doctor_name': doctor_name,
        'doctor_id': doctor_id,
        'patient_name': patient_name,
        'date': date,
        'medications': medications
    }
    
    # Generate hash
    prescription_hash = generate_prescription_hash(prescription_data)
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    meds_str = ','.join(medications)
    c.execute('''
        INSERT INTO prescriptions (code, doctor_name, doctor_id, patient_name, date, medications, hash)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (code, doctor_name, doctor_id, patient_name, date, meds_str, prescription_hash))
    conn.commit()
    conn.close()

def get_prescription(code):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM prescriptions WHERE code=?", (code,))
    result = c.fetchone()
    
    if result:
        # Create prescription data for verification
        prescription_data = {
            'code': result[0],
            'doctor_name': result[1],
            'doctor_id': result[2],
            'patient_name': result[3],
            'date': result[4],
            'medications': result[5].split(',')
        }
        
        # Verify hash
        stored_hash = result[6]  # Hash is the 7th column
        is_verified = verify_prescription_hash(stored_hash, prescription_data)
        
        # Add verification status to result
        result = result + (is_verified,)
    
    conn.close()
    return result


def find_prescription_by_hash(prescription_hash):
    """Find a prescription row by stored hash."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM prescriptions WHERE hash=?", (prescription_hash,))
    row = c.fetchone()
    conn.close()
    return row


def parse_prescription_text(text):
    """Heuristic parser to extract prescription fields from OCR'd text.

    Returns a dict with keys: code, doctor_name, doctor_id, patient_name, date, medications (list)
    Fields may be None if not found.
    """
    if not text:
        return None

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    data = {
        'code': None,
        'doctor_name': None,
        'doctor_id': None,
        'patient_name': None,
        'date': None,
        'medications': []
    }

    i = 0
    while i < len(lines):
        line = lines[i]
        low = line.lower()
        if 'prescription code' in low or (low.startswith('code') and ':' in line):
            parts = line.split(':', 1)
            data['code'] = parts[1].strip() if len(parts) > 1 else None
        elif line.lower().startswith('doctor name') or 'doctor:' in low:
            parts = line.split(':', 1)
            data['doctor_name'] = parts[1].strip() if len(parts) > 1 else None
        elif 'doctor id' in low or 'licence' in low or 'license' in low:
            parts = line.split(':', 1)
            data['doctor_id'] = parts[1].strip() if len(parts) > 1 else None
        elif line.lower().startswith('patient name') or line.lower().startswith('patient:'):
            parts = line.split(':', 1)
            data['patient_name'] = parts[1].strip() if len(parts) > 1 else None
        elif line.lower().startswith('date'):
            parts = line.split(':', 1)
            data['date'] = parts[1].strip() if len(parts) > 1 else None
        elif 'medications' in low or 'medicines' in low or 'drugs' in low:
            # collect following lines or parse comma-separated list on same line
            parts = line.split(':', 1)
            meds_text = parts[1].strip() if len(parts) > 1 else ''
            if meds_text:
                meds = [m.strip() for m in meds_text.split(',') if m.strip()]
                data['medications'].extend(meds)
            else:
                # grab subsequent lines until blank or next label
                j = i + 1
                while j < len(lines):
                    nxt = lines[j]
                    if any(k in nxt.lower() for k in ['doctor', 'patient', 'date', 'prescription', 'code']):
                        break
                    data['medications'].append(nxt)
                    j += 1
                i = j - 1
        i += 1

    # Final normalization: split any medications that contain commas
    meds_final = []
    for m in data['medications']:
        meds_final.extend([x.strip() for x in m.split(',') if x.strip()])
    data['medications'] = meds_final

    return data


def _normalize_text_field(s):
    """Normalize a text field for strict comparison: trim, collapse spaces, lowercase."""
    if s is None:
        return None
    return ' '.join(s.split()).strip().lower()


def _normalize_med_list(meds):
    if not meds:
        return []
    return [ _normalize_text_field(m) for m in meds ]


def _prescription_matches_row(parsed, row):
    """Compare parsed prescription dict to a DB row strictly after normalization.

    row is a tuple: (code, doctor_name, doctor_id, patient_name, date, medications, hash)
    Returns True only if all fields match exactly (after normalization) and medication lists match in order.
    """
    if not parsed or not row:
        return False

    # Build db dict
    db = {
        'code': row[0],
        'doctor_name': row[1],
        'doctor_id': row[2],
        'patient_name': row[3],
        'date': row[4],
        'medications': row[5].split(',') if row[5] else []
    }

    # Normalize and compare (strict)
    for key in ['code', 'doctor_name', 'doctor_id', 'patient_name', 'date']:
        pv = parsed.get(key)
        dv = db.get(key)
        if _normalize_text_field(pv) != _normalize_text_field(dv):
            break
    else:
        # medications: compare normalized lists and order
        parsed_meds = _normalize_med_list(parsed.get('medications', []))
        db_meds = _normalize_med_list(db.get('medications', []))
        if parsed_meds == db_meds:
            return True

    # Strict check failed — try a relaxed fuzzy comparison to tolerate small OCR differences
    from difflib import SequenceMatcher

    def similar(a, b):
        if a is None and b is None:
            return 1.0
        if a is None or b is None:
            return 0.0
        return SequenceMatcher(None, _normalize_text_field(a), _normalize_text_field(b)).ratio()

    thresh = 0.95  # high threshold: only tiny OCR deviations allowed
    fields = ['code', 'doctor_name', 'doctor_id', 'patient_name', 'date']
    for key in fields:
        score = similar(parsed.get(key), db.get(key))
        if score < thresh:
            # debug print to help troubleshoot mismatches
            print(f"[verify] field mismatch '{key}': parsed='{parsed.get(key)}' db='{db.get(key)}' score={score}")
            return False

    # compare medication lists: require same length and each item similar
    parsed_meds = _normalize_med_list(parsed.get('medications', []))
    db_meds = _normalize_med_list(db.get('medications', []))
    if len(parsed_meds) != len(db_meds):
        print(f"[verify] meds length mismatch: parsed={parsed_meds} db={db_meds}")
        return False
    for i, (pm, dm) in enumerate(zip(parsed_meds, db_meds)):
        score = SequenceMatcher(None, pm, dm).ratio()
        if score < thresh:
            print(f"[verify] med mismatch index {i}: parsed='{pm}' db='{dm}' score={score}")
            return False

    return True

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
        previous_code = get_previous_code()
        add_prescription(code, previous_code, doctor_name, doctor_id, patient_name, date, medications)
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
        extracted_text = None
        parsed_from_file = None
        # Check if file uploaded
        file = request.files.get('prescription')
        if file and file.filename != '':
            fname = file.filename.lower()
            # Handle PDF uploads
            if fname.endswith('.pdf') or file.mimetype == 'application/pdf':
                # read bytes once
                file_bytes = file.read()

                # 1) Try to extract text from PDF using PyPDF2 (if installed)
                try:
                    from PyPDF2 import PdfReader
                    reader = PdfReader(BytesIO(file_bytes))
                    extracted_text = ''
                    for page in reader.pages:
                        try:
                            extracted_text += (page.extract_text() or '') + "\n"
                        except Exception:
                            continue
                except Exception:
                    extracted_text = None

                # 2) If no code yet, try to decode QR from first PDF page using pdf2image (if available)
                if not code and not extracted_text:
                    try:
                        from pdf2image import convert_from_bytes
                        images = convert_from_bytes(file_bytes)
                        if images:
                            qr_data = decode(images[0])
                            if qr_data:
                                code = qr_data[0].data.decode('utf-8')
                    except Exception:
                        pass

                # 3) Fallback to OCR.Space for PDF if we don't have extracted_text or code
                if not extracted_text:
                    try:
                        response = requests.post(
                            "https://api.ocr.space/parse/image",
                            files={"filename": ("prescription.pdf", file_bytes)},
                            data={"apikey": OCR_API_KEY, "language": "eng"}
                        )
                        result = response.json()
                        parsed_results = result.get("ParsedResults")
                        if parsed_results:
                            extracted_text = parsed_results[0].get("ParsedText", "")
                            for line in extracted_text.split("\n"):
                                if "Prescription Code" in line or "Code" in line:
                                    code = line.split(":")[-1].strip()
                                    break
                    except Exception:
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
                            extracted_text = parsed_results[0].get("ParsedText", "")
                            for line in extracted_text.split("\n"):
                                if "Prescription Code" in line or "Code" in line:
                                    code = line.split(":")[-1].strip()
                                    break
                except Exception:
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
                            extracted_text = parsed_results[0].get("ParsedText", "")
                            for line in extracted_text.split("\n"):
                                if "Prescription Code" in line or "Code" in line:
                                    code = line.split(":")[-1].strip()
                                    break
                    except Exception:
                        pass

        # If code entered manually
        if not code:
            code = request.form.get('code', '').strip()

        # If we have a code: verify by code and, if possible, compare with uploaded file content
        if code:
            db_entry = get_prescription(code)
            if not db_entry:
                return f"Prescription code {code} NOT found in database."

            # If we also extracted text from an uploaded file, attempt to parse it and compare hashes
            if extracted_text:
                parsed_from_file = parse_prescription_text(extracted_text)
                if parsed_from_file:
                    file_hash = generate_prescription_hash(parsed_from_file)
                    stored_hash = db_entry[6] if len(db_entry) > 6 else None
                    if stored_hash and file_hash != stored_hash:
                        # Uploaded file does not match the stored prescription with this code
                        doctor_name = parsed_from_file.get('doctor_name') or ''
                        doctor_id = parsed_from_file.get('doctor_id') or ''
                        patient_name = parsed_from_file.get('patient_name') or ''
                        date = parsed_from_file.get('date') or ''
                        medications = parsed_from_file.get('medications') or []
                        return render_template('verify_result.html', code=code, doctor_name=doctor_name, doctor_id=doctor_id, patient_name=patient_name, date=date, medications=medications, is_verified=False, prescription_hash=file_hash)

            # No mismatch found (or no uploaded file to compare) -> render DB entry as verified
            doctor_name, doctor_id, patient_name, date, medications = db_entry[1], db_entry[2], db_entry[3], db_entry[4], db_entry[5].split(',')
            prescription_hash = db_entry[6] if len(db_entry) > 6 else None
            is_verified = True
            return render_template('verify_result.html', code=code, doctor_name=doctor_name, doctor_id=doctor_id, patient_name=patient_name, date=date, medications=medications, is_verified=is_verified, prescription_hash=prescription_hash)

        # If no code but we have extracted text from a file: try to parse and find by hash
        if extracted_text:
            parsed_from_file = parse_prescription_text(extracted_text)
            if parsed_from_file:
                file_hash = generate_prescription_hash(parsed_from_file)
                row = find_prescription_by_hash(file_hash)
                if row:
                    # Found a matching stored prescription: render it as verified
                    doctor_name, doctor_id, patient_name, date, medications = row[1], row[2], row[3], row[4], row[5].split(',')
                    prescription_hash = row[6] if len(row) > 6 else None
                    is_verified = True
                    return render_template('verify_result.html', code=row[0], doctor_name=doctor_name, doctor_id=doctor_id, patient_name=patient_name, date=date, medications=medications, is_verified=is_verified, prescription_hash=prescription_hash)
                else:
                    # Not in DB: show rejected result with parsed fields and file hash
                    doctor_name = parsed_from_file.get('doctor_name') or ''
                    doctor_id = parsed_from_file.get('doctor_id') or ''
                    patient_name = parsed_from_file.get('patient_name') or ''
                    date = parsed_from_file.get('date') or ''
                    medications = parsed_from_file.get('medications') or []
                    return render_template('verify_result.html', code='', doctor_name=doctor_name, doctor_id=doctor_id, patient_name=patient_name, date=date, medications=medications, is_verified=False, prescription_hash=file_hash)

        # No code and no parseable text -> cannot verify
        return "Cannot detect prescription code or extract prescription data from the uploaded file."

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
