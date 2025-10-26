from flask import Flask, request, send_file, session, redirect, url_for, render_template
import requests
import sqlite3
import random
import hashlib
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
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
OCR_API_KEY = os.getenv('OCR_API_KEY')

app = Flask(__name__)
app.secret_key = "supersecretkey123"  # Change in production
DB_FILE = "prescriptions.db"

# -------------------
# Make username + role available in ALL templates
# -------------------
@app.context_processor
def inject_user():
    # This ensures templates can always reference `username` and `role`
    return {
        'username': session.get('username'),
        'role': session.get('role')
    }

# -------------------
# Helper Functions
# -------------------

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
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
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT,
        name TEXT,
        license_id TEXT,
        organization TEXT
    )''')

    conn.commit()
    conn.close()

def generate_code(length=8):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def get_previous_hash():
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
    previous_hash = get_previous_hash()
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    meds_str = ','.join(medications)
    c.execute('''
        INSERT INTO prescriptions (code, doctor_name, doctor_id, patient_name, date, medications, hash, previous_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (code, doctor_name, doctor_id, patient_name, date, meds_str, prescription_hash, previous_hash))

    conn.commit()
    conn.close()

def get_prescription(code):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM prescriptions WHERE code=?", (code,))
    result = c.fetchone()
    conn.close()
    return result

def generate_prescription_hash(prescription_data):
    data_string = json.dumps(prescription_data, sort_keys=True)

    hash_object = hashlib.sha256(data_string.encode())
    prescription_hash = hash_object.hexdigest()

    return prescription_hash

def parse_prescription_text(text):
    """Simple heuristic parser."""
    if not text:
        return None
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    data = {'code': None, 'doctor_name': None, 'doctor_id': None,
            'patient_name': None, 'date': None, 'medications': []}
    for i, line in enumerate(lines):
        low = line.lower()
        if 'code' in low:
            data['code'] = line.split(':')[-1].strip()
        elif 'doctor name' in low:
            data['doctor_name'] = line.split(':')[-1].strip()
        elif 'doctor id' in low or 'license' in low:
            data['doctor_id'] = line.split(':')[-1].strip()
        elif 'patient name' in low:
            data['patient_name'] = line.split(':')[-1].strip()
        elif 'date' in low:
            data['date'] = line.split(':')[-1].strip()
        elif 'medications' in low or 'medicines' in low:
            meds = line.split(':')[-1].strip()
            if meds:
                data['medications'] = [m.strip() for m in meds.split(',')]
            else:
                # grab next lines
                j = i + 1
                while j < len(lines) and not any(k in lines[j].lower() for k in ['doctor','patient','code','date']):
                    data['medications'].append(lines[j].strip())
                    j += 1
    return data

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
    # templates can use `username` and `role` directly thanks to inject_user()
    return render_template('home.html')

@app.route('/signup', methods=['GET','POST'])
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
            c.execute('''INSERT INTO users (username, password, role, name, license_id, organization)
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (username, hashed_pw, role, name, license_id, organization))
            conn.commit()
        except sqlite3.IntegrityError:
            return "Username already exists"
        conn.close()
        message = "Signup successful! You can now login."
        return render_template('message.html', title='Signup Successful', message=message, link_url=url_for('login'), link_text='Login')
    return render_template('signup.html')

@app.route('/login', methods=['GET','POST'])
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
            return render_template('message.html', title='Login Failed', message="Invalid username or password.", link_url=url_for('login'), link_text='Try Again')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/create', methods=['GET','POST'])
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

@app.route('/verify', methods=['GET','POST'])
@login_required
@role_required('verifier')
def verify():
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        file = request.files.get('prescription')
        parsed_from_file = None

        # Parse file if uploaded
        if file and file.filename != '':
            file.seek(0)
            fname = file.filename.lower()
            try:
                if fname.endswith('.pdf'):
                    from PyPDF2 import PdfReader
                    reader = PdfReader(file)
                    extracted_text = ''
                    for page in reader.pages:
                        extracted_text += (page.extract_text() or '') + '\n'
                    parsed_from_file = parse_prescription_text(extracted_text)
                else:
                    img = Image.open(file)
                    qr_data = decode(img)
                    if qr_data:
                        code = qr_data[0].data.decode('utf-8')
                    else:
                        file.seek(0)
                        file_bytes = file.read()
                        response = requests.post(
                            "https://api.ocr.space/parse/image",
                            files={"filename": ("image.png", file_bytes)},
                            data={"apikey": OCR_API_KEY, "language": "eng"}
                        )
                        result = response.json()
                        parsed_results = result.get("ParsedResults")
                        if parsed_results:
                            extracted_text = parsed_results[0].get("ParsedText", "")
                            parsed_from_file = parse_prescription_text(extracted_text)
            except Exception as e:
                print("File parse error:", e)

        # Verify code
        if code:
            print("code")
            db_entry = get_prescription(code)
            if not db_entry:
                return f"Prescription code {code} NOT found in database."
              
            # Show DB entry
            doctor_name, doctor_id, patient_name, date, medications = db_entry[1], db_entry[2], db_entry[3], db_entry[4], db_entry[5].split(',')
            stored_hash = db_entry[6]
            is_verified = True
            return render_template('verify_result.html', code=code, doctor_name=doctor_name, doctor_id=doctor_id,
                                   patient_name=patient_name, date=date, medications=medications, is_verified=is_verified)

        # If no code but parsed from file
        if parsed_from_file and parsed_from_file.get('code'):
            print("parse")
            db_entry = get_prescription(parsed_from_file['code'])
            if db_entry:
                doctor_name, doctor_id, patient_name, date, medications = db_entry[1], db_entry[2], db_entry[3], db_entry[4], db_entry[5].split(',')

                prescription_data = {
                    'code': parsed_from_file["code"],
                    'doctor_name': parsed_from_file["doctor_name"],
                    'doctor_id': parsed_from_file["doctor_id"],
                    'patient_name': parsed_from_file["patient_name"],
                    'date': parsed_from_file["date"],
                    'medications': parsed_from_file["medications"]
                }

                print("prescription_data")

                stored_hash = db_entry[6]
                user_hash = generate_hash
                print(stored_hash)
                print(user_hash)
                is_verified = stored_hash == user_hash
                return render_template('verify_result.html', code=parsed_from_file['code'], doctor_name=doctor_name,
                                       doctor_id=doctor_id, patient_name=patient_name, date=date,
                                       medications=medications, is_verified=is_verified)
            else:
                return render_template('verify_result.html', code=parsed_from_file.get('code',''),
                                       doctor_name=parsed_from_file.get('doctor_name',''),
                                       doctor_id=parsed_from_file.get('doctor_id',''),
                                       patient_name=parsed_from_file.get('patient_name',''),
                                       date=parsed_from_file.get('date',''),
                                       medications=parsed_from_file.get('medications',[]),
                                       is_verified=False)
        return "Cannot detect prescription code or extract prescription data from the uploaded file."
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
