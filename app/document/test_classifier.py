from document_classifier import classify_document


items = [
    {"text": "INVOICE", "confidence": 0.99},
    {"text": "Invoice Number FA2022-0001", "confidence": 0.98},
    {"text": "Invoice Date 05/09/2022", "confidence": 0.97},
    {"text": "VAT Number BE0631922138", "confidence": 0.96},
    {"text": "Total €181,50", "confidence": 0.98}
]


result = classify_document(items)

print(result)