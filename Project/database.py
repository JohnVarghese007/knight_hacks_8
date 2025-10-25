import sqlite3

# Connect to database (creates file if it doesn't exist)
conn = sqlite3.connect('prescriptions.db')
c = conn.cursor()

# Create prescriptions table
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

print("Database created and table ready!")
