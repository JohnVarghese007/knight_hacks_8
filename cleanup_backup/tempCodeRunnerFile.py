from flask import Flask, request
import requests
import sqlite3
import random
import string

app = Flask(__name__)

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

# -------------------
# Routes
# -------------------

# Home page
@app.route('/')
def home():
    return '''
    <h2>Prescription System</h2>
    <p><a href="/create">Doctor: Create Prescription</a></p>
    <p><a href="/verify">Officer: Verify Prescription by Image</a></p>
    <p><a href="/verify_code">Officer: Verify Prescription by Code</a></p>
    '''

# Doctor: create prescription
@app.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        doctor_name = request.form['doctor_name']
        doctor_id = request.form['doctor_id']
        patient_name = request.form['patient_name']
        date = request.form['date']
        medications = request.form['medications'].split(',')
        code = generate_code()
        add_prescription(code, doctor_name, doctor_id, patient_name, date, medications)
        return f"<h3>Prescription Created!</h3><p>Code: {code}</p><p><a href='/'>Home</a></p>"

    return '''
    <h2>Create Prescription (Doctor)</h2>
    <form method="POST">
        Doctor Name: <input type="text" name="doctor_name" required><br>
        Doctor ID: <input type="text" name="doctor_id" required><br>
        Patient Name: <input type="text" name="patient_name" required><br>
        Date: <input type="text" name="date" required><br>
        Medications (comma-separated): <input type="text" name="medications" required><br>
        <input type="submit" value="Create Prescription">
    </form>
    <p><a href='/'>Home</a></p>
    '''

# Officer: upload and verify via image
@app.route('/verify', methods=['GET', 'POST'])
def verify():
    if request.method == 'POST':
        file = request.files.get('prescription')
        if not file:
            return "No file uploaded"

        file_bytes = file.read()

        # OCR request
        response = requests.post(
            "https://api.ocr.space/parse/image",
            files={"filename": ("prescription.png", file_bytes)},
            data={"apikey": OCR_API_KEY, "language": "eng"}
        )
        result = response.json()
        parsed_results = result.get("ParsedResults")
        if not parsed_results:
            return f"OCR failed. API response: {result}"

        text = parsed_results[0].get("ParsedText", "")
        lines = text.split("\n")

        # Extract prescription code from OCR
        code = None
        for line in lines:
            if "Prescription Code" in line or "Code" in line:
                code = line.split(":")[-1].strip()
                break

        if not code:
            return f"Prescription code not found in OCR text.<br>Raw OCR:<pre>{text}</pre>"

        db_entry = get_prescription(code)
        if not db_entry:
            return f"Prescription code {code} NOT found in database.<br>Raw OCR:<pre>{text}</pre>"

        # Show database entry
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

    return '''
    <h2>Verify Prescription by Image</h2>
    <form method="POST" enctype="multipart/form-data">
        Upload Prescription Image: <input type="file" name="prescription" accept="image/*" required><br>
        <input type="submit" value="Verify Prescription">
    </form>
    <p><a href='/'>Home</a></p>
    '''

# Officer: verify by entering code directly
@app.route('/verify_code', methods=['GET', 'POST'])
def verify_code():
    if request.method == 'POST':
        code = request.form.get('code').strip()
        db_entry = get_prescription(code)
        if not db_entry:
            return f"Prescription code {code} NOT found in database.<br><a href='/verify_code'>Try Again</a>"

        doctor_name, doctor_id, patient_name, date, medications = db_entry[1], db_entry[2], db_entry[3], db_entry[4], db_entry[5].split(',')
        return f"""
        <h3>Prescription Found ✅</h3>
        <h4>Details:</h4>
        <pre>
        Code: {code}
        Doctor Name: {doctor_name}
        Doctor ID: {doctor_id}
        Patient Name: {patient_name}
        Date: {date}
        Medications: {', '.join(medications)}
        </pre>
        <p><a href='/verify_code'>Verify Another</a></p>
        <p><a href='/'>Home</a></p>
        """

    return '''
    <h2>Verify Prescription by Code</h2>
    <form method="POST">
        Enter Prescription Code: <input type="text" name="code" required><br>
        <input type="submit" value="Verify">
    </form>
    <p><a href='/'>Home</a></p>
    '''

# -------------------
# Run App
# -------------------
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
