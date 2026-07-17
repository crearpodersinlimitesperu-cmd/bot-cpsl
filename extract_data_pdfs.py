import PyPDF2
import os
import sys

# Asegurar UTF-8
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

def extract_pdf_data(pdf_path):
    print(f"\n--- DATA EXTRACT: {os.path.basename(pdf_path)} ---")
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        return
    
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            num_pages = len(reader.pages)
            print(f"Total pages: {num_pages}")
            
            # Extract text from all pages but only print relevant data rows
            for i in range(num_pages):
                page = reader.pages[i]
                text = page.extract_text()
                lines = text.split('\n')
                for line in lines:
                    # Look for lines that look like data (DNI, phone numbers, names)
                    if any(char.isdigit() for char in line) and len(line) > 10:
                        print(line)
    except Exception as e:
        print(f"Error reading PDF: {e}")

pdfs = [
    r"C:\Users\josem\Downloads\CREACION CUANTICA E.I.R.L_29-31.05.2026 Lista de espera.pdf",
    r"C:\Users\josem\Downloads\CREACION CUANTICA E.I.R.L_29-31.05.2026 V2.pdf"
]

if __name__ == "__main__":
    for pdf in pdfs:
        extract_pdf_data(pdf)
