from flask import Flask, request, jsonify
from rules import find_suspicious_terms
from text_utils import (text_hash, extract_total_amount, extract_date,
                        extract_merchant_info, extract_line_items, extract_amounts)
from ocr_utils import extract_text_from_pdf_enhanced, extract_text_from_image


app = Flask(__name__)

# In-memory storage
seen_receipts = set()
receipt_database = []

@app.route("/analyze-receipt", methods=["POST"])
def analyze_receipt():
    """Enhanced receipt analysis with ML-ready structure"""
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files["file"]
    file_bytes = file.read()
    
    # Determine file type and extract text
    filename = file.filename.lower()
    if filename.endswith('.pdf'):
        extracted_text = extract_text_from_pdf_enhanced(file_bytes)
    elif filename.endswith(('.jpg', '.jpeg', '.png')):
        extracted_text = extract_text_from_image(file_bytes)
    else:
        return jsonify({"error": "Unsupported file format"}), 400
    
    # Generate receipt ID
    receipt_id = text_hash(extracted_text)
    is_duplicate = receipt_id in seen_receipts
    seen_receipts.add(receipt_id)
    
    # Extract structured data
    merchant = extract_merchant_info(extracted_text)
    total_amount = extract_total_amount(extracted_text)
    transaction_date = extract_date(extracted_text)
    line_items = extract_line_items(extracted_text)
    all_amounts = extract_amounts(extracted_text)
    
    # Fraud detection
    suspicious_terms = find_suspicious_terms(extracted_text)
    
    # Calculate confidence score
    confidence_score = calculate_confidence(
        extracted_text, total_amount, transaction_date, line_items
    )
    
    # Prepare response
    receipt_data = {
        "receipt_id": receipt_id,
        "is_duplicate": is_duplicate,
        "merchant": merchant,
        "total_amount": total_amount,
        "transaction_date": transaction_date,
        "line_items": line_items,
        "all_amounts": all_amounts,
        "suspicious_terms": suspicious_terms,
        "confidence_score": confidence_score,
        "extracted_text": extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text
    }
    
    # Store for future ML training
    receipt_database.append(receipt_data)
    
    return jsonify(receipt_data)

def calculate_confidence(text, total, date, items):
    score = 0
    if text and len(text) > 50:
        score += 30   # Text extracted
    if total is not None:
        score += 35   # Total found (most important)
    if date:
        score += 15   # Date is optional bonus
    if items and len(items) > 0:
        score += 20   # Line items found
    return score

@app.route("/receipts", methods=["GET"])
def get_all_receipts():
    """Retrieve all processed receipts (for ML training data)"""
    return jsonify({
        "total_receipts": len(receipt_database),
        "receipts": receipt_database
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
