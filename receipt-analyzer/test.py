import os
import sys
import mimetypes
import requests

API_BASE = os.getenv("API_BASE", "http://localhost:5001")
ANALYZE_URL = f"{API_BASE}/analyze-receipt"


def guess_content_type(path: str) -> str:
    ctype, _ = mimetypes.guess_type(path)
    return ctype or "application/octet-stream"


def main():
    # Usage:
    #   python test.py E:\Synclife\sample_receipt_template.png
    #   python test.py .\receipt.jpg
    #   API_BASE=http://127.0.0.1:5001 python test.py .\receipt.png

    if len(sys.argv) < 2:
        print("Usage: python test.py <path-to-receipt-image-or-pdf>")
        print("Example: python test.py E:\\Synclife\\sample_receipt_template.png")
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"ERROR: File not found: {file_path}")
        sys.exit(1)

    content_type = guess_content_type(file_path)

    try:
        with open(file_path, "rb") as f:
            files = {
                "file": (os.path.basename(file_path), f, content_type)
            }
            resp = requests.post(ANALYZE_URL, files=files, timeout=120)

        print("URL:", ANALYZE_URL)
        print("Status:", resp.status_code)

        if resp.status_code >= 400:
            print("\n--- Response text (first 2000 chars) ---")
            print(resp.text[:2000])
            sys.exit(2)

        try:
            data = resp.json()
        except Exception:
            print("ERROR: Server returned non-JSON response")
            print(resp.text[:2000])
            sys.exit(3)

        extracted_preview = data.get("extracted_text", "")
        if isinstance(extracted_preview, str) and len(extracted_preview) > 500:
            data["extracted_text"] = extracted_preview[:500] + "..."

        import json
        print("\n--- JSON ---")
        print(json.dumps(data, indent=2, ensure_ascii=False))

    except requests.exceptions.ConnectionError:
        print("ERROR: Cannot connect to the server.")
        print("Make sure Flask is running in another terminal: python app.py")
        print("And that the URL is reachable:", ANALYZE_URL)
        sys.exit(4)
    except requests.exceptions.Timeout:
        print("ERROR: Request timed out (OCR can be slow). Try again or use a smaller image.")
        sys.exit(5)


if __name__ == "__main__":
    main()
