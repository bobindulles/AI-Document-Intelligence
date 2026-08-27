from document_processor import process_document

file_path = "data/raw/invoice-example-comanage.pdf"

result = process_document(file_path)

print("Processed files:")
print(result)