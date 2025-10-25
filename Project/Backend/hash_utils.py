import hashlib
import json

def generate_prescription_hash(prescription_data):
    """
    Generate a unique hash for prescription data using SHA-256
    """
    # Convert prescription data to a sorted JSON string to ensure consistent hashing
    data_string = json.dumps(prescription_data, sort_keys=True)
    
    # Create SHA-256 hash
    hash_object = hashlib.sha256(data_string.encode())
    prescription_hash = hash_object.hexdigest()
    
    return prescription_hash

def verify_prescription_hash(stored_hash, prescription_data):
    """
    Verify if the prescription data matches the stored hash
    """
    # Generate hash from current data
    current_hash = generate_prescription_hash(prescription_data)
    
    # Compare with stored hash
    return stored_hash == current_hash