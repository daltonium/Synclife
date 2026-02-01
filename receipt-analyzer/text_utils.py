import hashlib
import re
from datetime import datetime

def text_hash(text):
    return hashlib.md5(text.encode()).hexdigest()

def extract_amounts(text):
    """Extract all monetary amounts from receipt"""
    # Support multiple currency symbols
    patterns = [
        r'₹\s?([0-9,]+\.?[0-9]*)',  # Rupees
        r'Rs\.?\s?([0-9,]+\.?[0-9]*)',  # Rupees alternative
        r'\$\s?([0-9,]+\.?[0-9]*)',  # Dollars
        r'€\s?([0-9,]+\.?[0-9]*)',  # Euros
    ]
    
    amounts = []
    for pattern in patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            amount_str = match.group(1).replace(",", "")
            try:
                amounts.append(float(amount_str))
            except ValueError:
                continue
    
    return amounts

def extract_total_amount(text):
    """Extract the final total amount"""
    # Look for total indicators
    total_patterns = [
        r'(?:total|grand total|amount|net amount)[\s:]*₹?\s?([0-9,]+\.?[0-9]*)',
        r'(?:total|grand total|amount|net amount)[\s:]*Rs\.?\s?([0-9,]+\.?[0-9]*)',
    ]
    
    for pattern in total_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount_str = match.group(1).replace(",", "")
            try:
                return float(amount_str)
            except ValueError:
                continue
    
    # Fallback: return largest amount
    amounts = extract_amounts(text)
    return max(amounts) if amounts else None

def extract_date(text):
    """Extract transaction date from receipt"""
    date_patterns = [
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',  # DD/MM/YYYY or MM/DD/YYYY
        r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',    # YYYY/MM/DD
        r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})',
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None

def extract_merchant_info(text):
    """Extract merchant name (typically in first few lines)"""
    lines = text.strip().split('\n')
    # Usually merchant name is in first 3 lines
    merchant_candidates = [line.strip() for line in lines[:3] if line.strip()]
    
    # Return first non-empty line as merchant name
    return merchant_candidates[0] if merchant_candidates else "Unknown"

def extract_line_items(text):
    """Extract individual line items with prices"""
    lines = text.split('\n')
    line_items = []
    
    for line in lines:
        # Look for lines with item description followed by amount
        match = re.search(r'(.+?)[\s\.]+₹?\s?([0-9,]+\.?[0-9]*)\s*$', line)
        if match:
            item_name = match.group(1).strip()
            price_str = match.group(2).replace(",", "")
            try:
                price = float(price_str)
                line_items.append({
                    "item": item_name,
                    "price": price
                })
            except ValueError:
                continue
    
    return line_items
