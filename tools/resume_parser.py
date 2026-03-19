import pdfplumber
import os

def parse_resume(pdf_path: str) -> dict:
    """Extracts text and basic info from resume PDF."""
    
    full_text = ""
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            full_text += page.extract_text() or ""
    
    return {
        "full_text": full_text,
        "pdf_path": pdf_path,
        "name":     extract_name(full_text),
        "email":    extract_email(full_text),
        "phone":    extract_phone(full_text),
    }

def extract_name(text: str) -> str:
    """First non-empty line is usually the name."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    return lines[0] if lines else "Candidate"

def extract_email(text: str) -> str:
    import re
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    return match.group(0) if match else ""

def extract_phone(text: str) -> str:
    import re
    match = re.search(r'[\+\d][\d\s\-]{9,14}', text)
    return match.group(0) if match else ""
