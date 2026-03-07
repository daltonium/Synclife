import hashlib
import re


def text_hash(text):
    return hashlib.md5(text.encode()).hexdigest()


def extract_amounts(text):
    """Extract amounts - handles $-prefixed AND plain decimal numbers"""
    amounts = []

    # Currency-prefixed amounts
    prefixed = re.findall(r'[$₹€]\s?([0-9,]+\.[0-9]{2})', text)
    for a in prefixed:
        try:
            amounts.append(float(a.replace(",", "")))
        except ValueError:
            continue

    # Plain decimal numbers (e.g. Walmart style: "1.97 X")
    # Only grab numbers that look like prices (1-4 digits, 2 decimal places)
    plain = re.findall(r'(?<!\d)(\d{1,4}\.\d{2})(?!\d)', text)
    for a in plain:
        try:
            val = float(a)
            if 0.01 <= val <= 99999:
                amounts.append(val)
        except ValueError:
            continue

    # Deduplicate while preserving order
    seen = set()
    result = []
    for x in amounts:
        if x not in seen:
            seen.add(x)
            result.append(x)
    return result


def extract_total_amount(text):
    """Extract final total - handles $-prefixed and plain number formats"""
    # Strong explicit total patterns
    patterns = [
        r'(?<!\w)total\s*\(usd\)[\s:]*\$?\s?([0-9,]+\.[0-9]{2})',
        r'grand\s+total[\s:]*\$?\s?([0-9,]+\.[0-9]{2})',
        r'(?<!\w)total[\s:]+\$([0-9,]+\.[0-9]{2})',
        r'(?<!\w)total[\s:]+([0-9,]+\.[0-9]{2})',   # Plain number total
        r'(?<!\w)total\s+amount[\s:]*\$?\s?([0-9,]+\.[0-9]{2})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1).replace(",", ""))
            except ValueError:
                continue

    # Fallback: largest amount found
    amounts = extract_amounts(text)
    return max(amounts) if amounts else None


def extract_amount(text):
    """Legacy single-amount extractor"""
    match = re.search(r'₹\s?([0-9,]+)', text)
    if match:
        return int(match.group(1).replace(",", ""))
    return None


def extract_date(text):
    date_patterns = [
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',
        r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})',
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

KNOWN_MERCHANTS = [
    'walmart', 'safeway', 'target', 'costco', 'kroger',
    'whole foods', 'amazon', 'cvs', 'walgreens', 'aldi',
    'trader joe', 'publix', 'meijer', 'heb', 'wegmans',
    'dollar general', 'dollar tree', 'home depot', 'lowes',
    'best buy', 'ikea', 'macdonalds', 'starbucks', 'subway'
]

def extract_merchant_info(text):
    """Find merchant - check known brands first, then heuristic scan"""
    text_lower = text.lower()

    # Step 1: Check for known merchant names anywhere in the text
    for merchant in KNOWN_MERCHANTS:
        if merchant in text_lower:
            return merchant.title()  # Returns "Safeway", "Walmart" etc.

    # Step 2: Heuristic scan of first 10 lines
    lines = text.strip().split('\n')
    noise_words = [
        'receipt', 'billed', 'upload', 'logo', 'invoice',
        'save money', 'live better', 'tax', 'total', 'subtotal',
        'st#', 'op#', 'te#', 'tr#', 'ref #', 'trans id',
        'terminal', 'validation', 'payment service', 'approval',
        'items sold', 'tc#', 'aid ', 'signature', 'change due',
        'customer copy', 'grocery', 'refrig', 'frozen', 'produce',
        'baked goods', 'meat', 'deli', 'liquor', 'miscellaneous',
        'regular price', 'card savings', 'qty', 'q1y', 'fiber',
        'reeder', 'resular', 'savinss', 'route'
    ]

    for line in lines[:10]:
        line = line.strip()
        if len(line) < 5:
            continue
        letter_ratio = len(re.findall(r'[a-zA-Z]', line)) / max(len(line), 1)
        if letter_ratio < 0.55:
            continue
        if any(n in line.lower() for n in noise_words):
            continue
        if re.search(r'[><\[\]\\|@#^*~`]', line):
            continue
        if re.search(r'\d{3}.*\d{3}.*\d{4}', line):
            continue
        # Skip lines with prices embedded
        if re.search(r'\d+\.\d{2}', line):
            continue
        return line

    return "Unknown"

def extract_line_items(text):
    lines = text.split('\n')
    line_items = []

    skip_keywords = [
        'subtotal', 'total', 'tax', 'balance', 'regular price',
        'card saving', 'card savin', 'regular', 'change', 'tend',
        'refrig', 'frozen', 'baked goods', 'meat', 'produce',
        'deli', 'liquor', 'grocery', 'miscellaneous', 'discount',
        'receipt #', 'visa', 'cash', 'approval', 'ref #',
        'trans', 'terminal', 'validation', 'payment', 'items sold',
        'tc#', 'aid', 'signature', 'change due', 'customer copy',
        'wt ', 'route', 'reeder', 'resular', 'savinss'
    ]

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if any(kw in line.lower() for kw in skip_keywords):
            continue

        # Format 1: "Description ... $90.00"
        match = re.search(r'^(.+?)\s+\$([0-9,]+\.[0-9]{2})\s*$', line)
        if match:
            item_name = match.group(1).strip()
            try:
                price = float(match.group(2).replace(",", ""))
                if price > 0:
                    line_items.append({"item": item_name, "price": price})
                    continue
            except ValueError:
                pass

        # Format 2: Walmart "ITEM_NAME  BARCODE  PRICE  FLAG"
        match = re.search(
            r'^([A-Z][A-Z0-9 /\.\-]{2,}?)\s+\d{8,}\s+([0-9]+\.[0-9]{2})',
            line
        )
        if match:
            item_name = match.group(1).strip()
            try:
                price = float(match.group(2))
                if price > 0:
                    line_items.append({"item": item_name, "price": price})
                    continue
            except ValueError:
                pass

        # Format 3: Grocery "ITEM NAME   5.00 S" or "ITEM NAME   5.00"
        # Handles: S/T/N tax flags, OCR misread flags (5 instead of S)
        match = re.search(
            r'^([A-Za-z][A-Za-z0-9 /\.\-]{2,}?)\s+([0-9]+\.[0-9]{2})\s*[A-Z0-9]?\s*$',
            line
        )
        if match:
            item_name = match.group(1).strip()
            # Extra skip check for section headers
            skip2 = ['subtotal', 'total', 'tax', 'balance', 'price',
                     'saving', 'refrig', 'frozen', 'produce', 'baked',
                     'meat', 'deli', 'liquor', 'grocery', 'misc']
            if any(s in item_name.lower() for s in skip2):
                continue
            try:
                price = float(match.group(2))
                if price > 0:
                    line_items.append({"item": item_name, "price": price})
            except ValueError:
                pass

    return line_items

