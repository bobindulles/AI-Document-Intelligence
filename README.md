# AI Document Intelligence and Verification System

An intelligent document processing system that combines Optical Character Recognition (OCR), document classification, information extraction, field validation, and machine-learning-based anomaly detection.

## Overview

The AI Document Intelligence and Verification System is designed to automate the extraction and analysis of information from semi-structured and unstructured documents, including invoices, certificates, and resumes.

The system processes uploaded documents, extracts their text, identifies their document category, retrieves relevant fields, and validates extracted information using configured rules. It also uses an unsupervised machine learning model to identify unusual invoice transactions for further review.

The goal is to reduce manual document processing, improve data accessibility, and assist users in identifying inconsistencies and potentially anomalous records.

## Key Features

- **OCR-based text extraction:** Extracts text from supported document images and PDFs using PaddleOCR.
- **PDF processing:** Converts PDF pages into images for OCR processing using PyMuPDF.
- **Document classification:** Categorizes documents using implemented keyword-based classification rules.
- **Information extraction:** Extracts relevant fields based on document type.
- **Field validation:** Checks extracted fields against configured validation rules.
- **Invoice anomaly detection:** Uses the Isolation Forest algorithm to identify unusual invoice transaction records.
- **Modular architecture:** Separates document processing, extraction, validation, and anomaly analysis into reusable components.

## Supported Document Types

### 1. Invoices

The system can extract supported invoice fields, including:

- Invoice number
- Invoice date
- VAT number
- Total amount

### 2. Certificates

Supported fields may include:

- Recipient name
- Certificate title
- Course name
- Issuing organization
- Certificate ID
- Issue date
- Expiry date
- Verification URL

### 3. Resumes

The system supports resume text extraction and document classification. The specific fields extracted depend on the implemented rules.

## System Workflow

1. Upload a supported document.
2. Convert PDF pages into images when required.
3. Extract text using OCR.
4. Classify the document using the implemented classification logic.
5. Extract relevant fields based on the document category.
6. Validate extracted values using configured rules.
7. For invoice transaction data, apply anomaly detection.
8. Present the extracted information and anomaly indicators for review.

## Technologies Used

| Technology | Purpose |
|---|---|
| Python | Core application development |
| PaddleOCR | Optical character recognition |
| PyMuPDF | PDF processing and page conversion |
| Regular expressions and rule-based logic | Field extraction and validation |
| Natural language processing techniques | Text processing and document analysis |
| Scikit-learn | Machine learning and anomaly detection |
| Isolation Forest | Unsupervised detection of unusual invoice transactions |

*Update this list to match the final dependencies actually used in the repository.*

## Anomaly Detection

The anomaly detection component uses the Isolation Forest algorithm to identify invoice transactions that differ from expected patterns in the structured data.

The model was developed using a synthetic dataset containing 10,000 invoice records and 11 columns. Feature engineering includes transaction-related attributes such as quantity, amount, amount per quantity, date components, product frequency, and stock frequency.

The model configuration uses:

- Algorithm: Isolation Forest
- Number of estimators: 200
- Contamination parameter: 0.05
- Random state: 42

The model flags records that may warrant further investigation. An anomaly score or flag is not proof of fraud; flagged records require human review and supporting evidence.

## Project Structure

The following is an example structure. Adjust it to match the final repository.

```text
AI-Document-Intelligence/
├── app/
│   ├── main.py
│   ├── ocr/
│   ├── extraction/
│   ├── classification/
│   ├── validation/
│   └── anomaly_detection/
├── data/
│   └── sample_data/
├── tests/
├── requirements.txt
├── .gitignore
└── README.md
```

## Installation

### Prerequisites

- Python version compatible with the project's dependencies
- Git
- Visual Studio Code or another Python development environment

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd AI-Document-Intelligence
```

Replace the placeholder with the actual repository URL.

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it on Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure OCR dependencies

Follow the installation instructions for the OCR engine and any required system dependencies used by the final implementation. Verify that the installed versions are compatible with your Python environment.

## Usage

Run the application using the actual entry point configured in the repository. For example:

```bash
python -m app.main
```

If the project uses a different entry point or requires command-line arguments, replace this command with the verified startup instructions.

Typical usage:

1. Provide a supported document.
2. Run the document-processing pipeline.
3. Review the detected document category.
4. Inspect the extracted fields and validation results.
5. Review any invoice records flagged by the anomaly detection model.

## Testing

Run the project's automated tests, if configured:

```bash
python -m pytest
```

If tests have not been configured, document the manual test procedure and the sample documents used to evaluate OCR, classification, extraction, validation, and anomaly detection.

## Limitations

- OCR accuracy depends on document quality, image resolution, orientation, fonts, and layout.
- Rule-based extraction may not correctly handle every document template or unusual field format.
- Incorrect OCR output can affect subsequent extraction and validation.
- Anomaly detection identifies unusual patterns rather than proving fraud.
- Results depend on the quality and representativeness of the training data.
- Comprehensive visual tampering detection and precise localization of forged regions are not claimed unless implemented and evaluated.

## Future Enhancements

- Improve OCR accuracy on low-quality and complex documents.
- Expand field extraction to handle more document layouts and formats.
- Introduce layout-aware document understanding models.
- Add visual tampering analysis and metadata consistency checks.
- Develop a user interface for document uploads and result visualization.
- Evaluate the system using real-world datasets and documented performance metrics.
- Add stronger testing, logging, and error handling.

## Responsible Use

The system is intended to assist document review and identify records requiring further inspection. Extracted information and anomaly indicators should be reviewed before consequential decisions are made. The system should not be treated as an authoritative fraud detector or as a replacement for independent verification.

## Contributing

Contributions, bug reports, and suggestions are welcome. Please document proposed changes and test them before submitting a pull request.

## Author

Bobin Dulles 
AI & Data Science  
GitHub: (https://github.com/bobindulles/AI-Document-Intelligence)
