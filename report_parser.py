"""
report_parser.py  —  Feature 2: AI Medical Report De-fuzzer
Uses Google Gemini API (FREE) to parse blood test PDFs/images.

Free Limits:
- gemini-2.0-flash-lite : 1,000 requests/day
- gemini-2.5-flash      : 250 requests/day

Install: pip install google-generativeai PyMuPDF pillow python-dotenv
API Key: aistudio.google.com (free, no credit card)
"""

import os
import json
import re
import base64
import fitz          # PyMuPDF
from PIL import Image
import io
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

# ── Configure Gemini ───────────────────────────────────────────────────────────
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise EnvironmentError(
        "GOOGLE_API_KEY not found! "
        "Get free key from aistudio.google.com and add to .env file."
    )

genai.configure(api_key=GOOGLE_API_KEY)

# ── Model Selection ────────────────────────────────────────────────────────────
# Use gemini-2.0-flash-lite for max free requests (1000/day)
# Change to "gemini-2.5-flash" for better accuracy (250/day)
GEMINI_MODEL = "gemini-3.1-flash-lite"

# ── Prompt ────────────────────────────────────────────────────────────────────
EXTRACTION_PROMPT = """You are a medical report parser.
Look at this blood test or health report image carefully.

Extract ONLY these values if they are clearly present:
- age (years, integer)
- weight (kg, float)
- height (metres, float — if given in cm divide by 100)
- bmi (float, calculated or stated)
- blood_sugar_fasting (mg/dL, float)
- hba1c (%, float)
- total_cholesterol (mg/dL, float)
- hdl (mg/dL, float)
- ldl (mg/dL, float)
- triglycerides (mg/dL, float)
- systolic_bp (mmHg, integer)
- diastolic_bp (mmHg, integer)
- smoker (true or false, only if explicitly mentioned)

Rules:
- Return ONLY a valid JSON object. No explanation, no markdown, no backticks.
- Use null for any value not found.
- Example: {"age": 35, "weight": 72.5, "height": 1.75, "bmi": 23.7, "blood_sugar_fasting": null, ...}
"""


# ── PDF to Images ──────────────────────────────────────────────────────────────
def _pdf_to_pil_images(pdf_bytes: bytes) -> list:
    """Convert first 2 pages of PDF to PIL Image objects."""
    doc    = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    for page_num in range(min(2, len(doc))):
        page = doc[page_num]
        mat  = fitz.Matrix(2.0, 2.0)       # 2x zoom for clarity
        pix  = page.get_pixmap(matrix=mat)
        img  = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)
    doc.close()
    return images


def _bytes_to_pil(image_bytes: bytes) -> Image.Image:
    """Convert raw image bytes to PIL Image."""
    return Image.open(io.BytesIO(image_bytes))


# ── Core Parser ────────────────────────────────────────────────────────────────
def parse_report(file_bytes: bytes, filename: str) -> dict:
    """
    Main function — accepts file bytes + filename.
    Returns dict with:
      - extracted_metrics  : raw values from report
      - predictor_fields   : mapped fields ready for /predict endpoint
      - confidence         : % of fields found
      - model_used         : which Gemini model was used
    """
    filename_lower = filename.lower()

    # ── Build image list ───────────────────────────────────────────────────────
    try:
        if filename_lower.endswith(".pdf"):
            pil_images = _pdf_to_pil_images(file_bytes)
        elif filename_lower.endswith((".jpg", ".jpeg", ".png")):
            pil_images = [_bytes_to_pil(file_bytes)]
        else:
            return {"error": "Unsupported file. Upload PDF, JPG, or PNG."}
    except Exception as e:
        return {"error": f"Could not read file: {str(e)}"}

    if not pil_images:
        return {"error": "No readable pages found in the file."}

    # ── Call Gemini ────────────────────────────────────────────────────────────
    try:
        model    = genai.GenerativeModel(GEMINI_MODEL)
        # Pass all pages + prompt in one call
        content  = pil_images + [EXTRACTION_PROMPT]
        response = model.generate_content(content)
        raw_text = response.text.strip()
    except Exception as e:
        error_msg = str(e)
        # Helpful error messages
        if "quota" in error_msg.lower():
            return {"error": f"Daily quota exceeded. Try tomorrow or switch to {GEMINI_MODEL}."}
        elif "api_key" in error_msg.lower() or "invalid" in error_msg.lower():
            return {"error": "Invalid API key. Check your GOOGLE_API_KEY in .env file."}
        return {"error": f"Gemini API error: {error_msg}"}

    # ── Parse JSON response ────────────────────────────────────────────────────
    try:
        clean   = re.sub(r"```json|```", "", raw_text).strip()
        metrics = json.loads(clean)
    except json.JSONDecodeError:
        # Try to extract JSON from response
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if match:
            try:
                metrics = json.loads(match.group())
            except Exception:
                return {"error": "Could not parse Gemini response.", "raw": raw_text}
        else:
            return {"error": "Gemini did not return valid JSON.", "raw": raw_text}

    # ── Map to predictor fields + health flags ─────────────────────────────────
    predictor_fields = _map_to_predictor(metrics)
    found = sum(1 for v in metrics.values() if v is not None)
    total = len(metrics)

    return {
        "extracted_metrics": metrics,
        "predictor_fields":  predictor_fields,
        "confidence":        round(found / total * 100) if total else 0,
        "fields_found":      found,
        "fields_total":      total,
        "model_used":        GEMINI_MODEL,
        "raw_response":      raw_text,
    }


# ── Field Mapper ───────────────────────────────────────────────────────────────
def _map_to_predictor(metrics: dict) -> dict:
    """
    Maps extracted metrics to InsureIQ predictor input fields.
    Also generates health risk flags based on clinical thresholds.
    """
    fields = {}

    if metrics.get("age"):
        fields["age"] = int(metrics["age"])

    if metrics.get("weight"):
        fields["weight"] = float(metrics["weight"])

    if metrics.get("height"):
        h = float(metrics["height"])
        if h > 10:           # given in cm
            h = h / 100
        fields["height"] = round(h, 2)

    if metrics.get("bmi"):
        fields["bmi_override"] = float(metrics["bmi"])

    if metrics.get("smoker") is not None:
        fields["smoker"] = bool(metrics["smoker"])

    # ── Health Risk Flags ──────────────────────────────────────────────────────
    flags = []

    bs = metrics.get("blood_sugar_fasting")
    if bs:
        if bs > 126:
            flags.append(f"⚠️ High fasting blood sugar ({bs} mg/dL) — possible diabetes risk")
        elif bs > 100:
            flags.append(f"⚠️ Borderline blood sugar ({bs} mg/dL) — pre-diabetic range")

    hba1c = metrics.get("hba1c")
    if hba1c:
        if hba1c > 6.5:
            flags.append(f"🚨 HbA1c {hba1c}% — diabetic range, significantly impacts premium")
        elif hba1c > 5.7:
            flags.append(f"⚠️ HbA1c {hba1c}% — pre-diabetic range")

    chol = metrics.get("total_cholesterol")
    if chol and chol > 240:
        flags.append(f"⚠️ High cholesterol ({chol} mg/dL) — cardiovascular risk")

    sbp = metrics.get("systolic_bp")
    dbp = metrics.get("diastolic_bp")
    if sbp and dbp:
        if sbp > 140 or dbp > 90:
            flags.append(f"🚨 High BP ({sbp}/{dbp} mmHg) — hypertension detected")
        elif sbp > 130:
            flags.append(f"⚠️ Elevated BP ({sbp}/{dbp} mmHg) — stage 1 hypertension")

    ldl = metrics.get("ldl")
    if ldl and ldl > 160:
        flags.append(f"⚠️ High LDL ({ldl} mg/dL) — bad cholesterol elevated")

    trig = metrics.get("triglycerides")
    if trig and trig > 200:
        flags.append(f"⚠️ High triglycerides ({trig} mg/dL) — metabolic risk")

    fields["health_flags"] = flags
    return fields


# ── Model Switcher (call this to change model) ─────────────────────────────────
def set_model(model_name: str):
    """
    Switch between Gemini models.
    Options:
      - 'gemini-2.0-flash-lite'  → 1,000 requests/day (default)
      - 'gemini-2.5-flash'       → 250 requests/day (better accuracy)
    """
    global GEMINI_MODEL
    GEMINI_MODEL = model_name
    print(f"Switched to model: {GEMINI_MODEL}")
