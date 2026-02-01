SUSPICIOUS_TERMS = [
    "without tender",
    "emergency procurement",
    "single vendor",
    "urgent approval",
    "special sanction",
    "direct purchase",
    # Additional suspicious terms for receipt fraud detection
    "cash only",
    "no refund",
    "altered",
    "correction fluid",
    "white out",
    "handwritten total",
    "unofficial receipt"
]

def find_suspicious_terms(text):
    """Find suspicious terms in receipt/invoice text"""
    found = []
    text_lower = text.lower()

    for term in SUSPICIOUS_TERMS:
        if term in text_lower:
            found.append(term)

    return found
