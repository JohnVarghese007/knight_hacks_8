from flask import Flask, request, send_file, session, redirect, url_for
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
    if 'username' in session:
        logged_in_html = f"""
            <p>Logged in as: {session['username']} ({session['role']})</p>
            <p><a href="/logout">Logout</a></p>
        """
    else:
        logged_in_html = """
            <p><a href="/signup">Signup</a></p>
            <p><a href="/login">Login</a></p>
        """
    return f"""
        <h2>Prescription System</h2>
        {logged_in_html}
        <p><a href="/create">Issuer: Create Prescription</a></p>
        <p><a href="/verify">Verifier: Verify Prescription</a></p>
    """

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
        return "Signup successful! You can now <a href='/login'>login</a>."
    
    return '''
    <h2>Signup</h2>
    <form method="POST">
        Username: <input type="text" name="username" required><br>
        Password: <input type="password" name="password" required><br>
        Role: 
        <select name="role">
            <option value="issuer">Issuer (Doctor/Pharmacy)</option>
            <option value="verifier">Verifier (Police/Authority)</option>
        </select><br>
        Full Name: <input type="text" name="name" required><br>
        License/ID: <input type="text" name="license_id" required><br>
        Organization: <input type="text" name="organization" required><br>
        <input type="submit" value="Sign Up">
    </form>
    '''

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
            return "Invalid username or password."
    
    return '''
    <h2>Login</h2>
    <form method="POST">
        Username: <input type="text" name="username" required><br>
        Password: <input type="password" name="password" required><br>
        <input type="submit" value="Login">
    </form>
    '''

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
        return f"""
        <h3>Prescription Created!</h3>
        <p>Code: {code}</p>
        <p><a href='/download/{code}'>Download PDF with QR Code</a></p>
        <p><a href='/'>Home</a></p>
        """

    return '''
    <h2>Create Prescription (Issuer)</h2>
    <form method="POST">
        Doctor Name: <input type="text" name="doctor_name" required><br>
        Doctor ID: <input type="text" name="doctor_id" required><br>
        Patient Name: <input type="text" name="patient_name" required><br>
        Date: <input type="text" name="date" required><br>
        Medications (name:quantity, comma-separated): <input type="text" name="medications" required><br>
        <input type="submit" value="Create Prescription">
    </form>
    <p><a href='/'>Home</a></p>
    '''

# -------------------
# Verifier: Verify Prescription (Image/QR + Code)
# -------------------
@app.route('/verify', methods=['GET', 'POST'])
@login_required
@role_required('verifier')
def verify():
    if request.method == 'POST':
        code = None

        # Check if file was uploaded
        file = request.files.get('prescription')
        if file:
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

        # If code field is filled, use it (overrides OCR/QR if both provided)
        form_code = request.form.get('code', '').strip()
        if form_code:
            code = form_code

        if not code:
            return "Cannot detect prescription code. Please upload an image or enter a code."

        db_entry = get_prescription(code)
        if not db_entry:
            return f"Prescription code {code} NOT found in database."

        doctor_name, doctor_id, patient_name, date, medications = db_entry[1], db_entry[2], db_entry[3], db_entry[4], db_entry[5].split(',')
        return f"""
        <h3>Prescription Verified ✅</h3>
        <h4>Details from Database:</h4>
        <pre>
        Code: {code}
        Doctor Name: {doctor_name}
        Doctor ID: {doctor_id}
        Patient Name: {patient_name}
        Date: {date}
        Medications: {', '.join(medications)}
        </pre>
        <p><a href='/verify'>Verify Another</a></p>
        <p><a href='/'>Home</a></p>
        """

    # GET request: show combined form
    return '''
    <h2>Verify Prescription</h2>
    <form method="POST" enctype="multipart/form-data">
        Upload Prescription Image or QR Code: <input type="file" name="prescription" accept="image/*"><br>
        OR Enter Prescription Code: <input type="text" name="code"><br>
        <input type="submit" value="Verify Prescription">
    </form>
    <p><a href='/'>Home</a></p>
    '''

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
