import sqlite3

def add_prescription(code, doctor_name, doctor_id, patient_name, date, medications):
    conn = sqlite3.connect('prescriptions.db')
    c = conn.cursor()
    meds_str = ','.join(medications)  # Convert list to string
    c.execute('''
        INSERT INTO prescriptions (code, doctor_name, doctor_id, patient_name, date, medications)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (code, doctor_name, doctor_id, patient_name, date, meds_str))
    conn.commit()
    conn.close()
    print(f"Prescription {code} added!")

# Example usage
add_prescription(
    "ABC123XYZ",
    "Dr. John Doe",
    "123456",
    "Jane Smith",
    "25/10/2025",
    ["Paracetamol 500mg x10", "Ibuprofen 200mg x15"]
)
