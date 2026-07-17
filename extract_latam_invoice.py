import sys
from pypdf import PdfReader
import re
import json

def extract_info(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        
        # Simple extraction based on typical LATAM invoice patterns.
        # This will be refined based on the output.
        print(f"--- Extracted from {pdf_path} ---")
        print(text)
        print("-" * 40)
        
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")

if __name__ == "__main__":
    files = [
        r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\FACTURAS\LA5448499XKKO-30b3c0de-6663-4870-acc3-141995d50c8a-cuv-bill.pdf",
        r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\FACTURAS\LA4625048CDWN-cc99d9af-e92d-43b4-af97-26c527003c4e-cuv-bill.pdf",
        r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\FACTURAS\LA5446072ZDBI-35103017-0140-43d2-aaa3-c964b7f6eed9-cuv-bill.pdf",
        r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\FACTURAS\LA5444317BOUO-51200528-adbb-4204-acd5-f3a8d39c9ecb-cuv-bill.pdf"
    ]
    for f in files:
        extract_info(f)
