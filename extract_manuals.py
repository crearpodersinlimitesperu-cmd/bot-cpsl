import PyPDF2
import os
import sys

# Asegurar UTF-8
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

def extract_pdf_text(pdf_path):
    print(f"\n--- EXTRACTING: {os.path.basename(pdf_path)} ---")
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        return
    
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            num_pages = len(reader.pages)
            print(f"Total pages: {num_pages}")
            
            # Extract first 5 pages to get a good sample
            for i in range(min(5, num_pages)):
                page = reader.pages[i]
                text = page.extract_text()
                print(f"\n[PAGE {i+1}]\n")
                print(text[:1000] + "..." if len(text) > 1000 else text)
    except Exception as e:
        print(f"Error reading PDF: {e}")

pdfs = [
    r"C:\Users\josem\Downloads\CREACION CUANTICA E.I.R.L_29-31.05.2026 Lista de espera.pdf",
    r"C:\Users\josem\Downloads\CREACION CUANTICA E.I.R.L_29-31.05.2026 V2.pdf",
    r"C:\Users\josem\Downloads\MANUAL_GLOBAL_COLABORADORES_CREAR_2026.pdf",
    r"C:\Users\josem\Downloads\MANUAL_CORPORATIVO_CREAR_2026.pdf"
]

if __name__ == "__main__":
    for pdf in pdfs:
        extract_pdf_text(pdf)
