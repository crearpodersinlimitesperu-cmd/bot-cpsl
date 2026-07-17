import docx
import os
import sys

# Asegurar UTF-8
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

def extract_docx_text(docx_path):
    print(f"\n--- EXTRACTING DOCX: {os.path.basename(docx_path)} ---")
    if not os.path.exists(docx_path):
        print(f"File not found: {docx_path}")
        return
    
    try:
        doc = docx.Document(docx_path)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        
        text = '\n'.join(full_text)
        print(text[:2000] + "..." if len(text) > 2000 else text)
    except Exception as e:
        print(f"Error reading DOCX: {e}")

docx_files = [
    r"C:\Users\josem\Downloads\CREAR_LIMA_ANALISIS\CREAR_Manual_Operativo_C1_C2_2026.docx"
]

if __name__ == "__main__":
    for d in docx_files:
        extract_docx_text(d)
