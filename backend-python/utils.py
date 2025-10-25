from PIL import Image
import pytesseract

# path to tesseract.exe
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# function to extract text from image using pytesseract
# image must be .jpg
def extract_text(image_file_path)->str:
    try:
        img = Image.open(image_file_path)
        text = pytesseract.image_to_string(img)
        return text
    except Exception as e:
        return f"Error reading image (Make sure to enter a JPG file): {e}"