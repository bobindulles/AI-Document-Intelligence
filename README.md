# AI Document Intelligence

AI-powered document verification system with OCR, Computer Vision, NLP, and Machine Learning.

## Project Objective

The system analyzes documents, recognizes its format, classifies document types, extracts essential fields and finds anomalies in the document.

The system is supposed to process such document types as:

- Invoices
- Certificates
- Resumes

The project is implemented as a document intelligence and verification pipeline.

---

## Currently Implemented Modules

- Project set up
- Document loading through file picker
- PDFs and images processing
- PDF-to-image conversion
- OCR via PaddleOCR
- Filtering of OCR results by confidence value
- Document classification
- Fields extraction of invoices
- Fields extraction of certificates
- Fields extraction of resumes
- QR code detection for certificates
- Anomaly detection using Machine Learning
- Full-fledged document pipeline

---

## Workflow of the System

```text
Document
   │
   ▼
File Selection
   │
   ▼
PDF/Image Processing
   │
   ▼
PaddleOCR
   │
   ├──Text
   ├──Confidence
   └──Coordinates
   │
   ▼
Document Classification
   │
   ├──Invoice
   ├──Certificate
   └──Resume
   │
   ▼
Fields Extraction
   │
   ├──Invoice Fields
   ├──Certificate Fields
   └──Resume Fields
   │
   ▼
ML-based Anomaly Detection
   │
   ▼
Verification Results