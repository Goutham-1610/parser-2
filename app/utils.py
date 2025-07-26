# import io
# import pdfplumber
# import json

# def extract_text_from_pdf(content: bytes) -> str:
#     with pdfplumber.open(io.BytesIO(content)) as pdf:
#         text = "\n".join(page.extract_text() or "" for page in pdf.pages)
#     return text.strip()

# def clean_json_output(raw_text: str) -> dict:
#     raw_text = raw_text.strip()
#     if raw_text.startswith("```json"):
#         raw_text = raw_text[7:].strip()
#     elif raw_text.startswith("```"):
#         raw_text = raw_text[3:].strip()
#     if raw_text.endswith("```"):
#         raw_text = raw_text[:-3].strip()

#     try:
#         return json.loads(raw_text)
#     except json.JSONDecodeError:
#         print(f"JSON parse failed. Raw output:\n{raw_text}")
#         return {}


import io
import pdfplumber
import json
import fitz  # PyMuPDF

def extract_text_from_pdf(content: bytes) -> str:
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    return text.strip()

def clean_json_output(raw_text: str) -> dict:
    raw_text = raw_text.strip()
    if raw_text.startswith("```json"):
        raw_text = raw_text[7:].strip()
    elif raw_text.startswith("```"):
        raw_text = raw_text[3:].strip()
    if raw_text.endswith("```"):
        raw_text = raw_text[:-3].strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        print(f"JSON parse failed. Raw output:\n{raw_text}")
        return {}

def extract_links_from_pdf(content: bytes) -> dict:
    links = {"linkedin": "", "github": ""}
    try:
        doc = fitz.open(stream=content, filetype="pdf")
        for page in doc:
            for link in page.get_links():
                uri = link.get("uri", "")
                if "linkedin.com" in uri:
                    links["linkedin"] = uri
                elif "github.com" in uri:
                    links["github"] = uri
    except Exception as e:
        print("Error extracting links from PDF:", e)
    return links
