import os
import fitz
from PIL import Image

os.makedirs("data/processed", exist_ok=True)


def process_document(file_path):
    extension = os.path.splitext(file_path)[1].lower()

    if extension == ".pdf":
        return process_pdf(file_path)

    elif extension in [".jpg", ".jpeg", ".png"]:
        return process_image(file_path)

    else:
        raise ValueError("Unsupported file type")


def process_pdf(file_path):
    document = fitz.open(file_path)

    pages = []

    for page_number, page in enumerate(document):
        pixmap = page.get_pixmap()

        image_path = f"data/processed/page_{page_number + 1}.png"
        pixmap.save(image_path)

        pages.append(image_path)

    document.close()

    return pages


def process_image(file_path):
    image = Image.open(file_path)

    image_path = "data/processed/document.png"
    image.save(image_path)

    return [image_path]