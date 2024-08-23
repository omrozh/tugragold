from pdf2image import convert_from_path
import os


def process_pdf(pdf_uuid):
    pages = convert_from_path(f'documents/{pdf_uuid}.pdf', 200)
    os.system(f"mkdir documents/{pdf_uuid}")

    for count, page in enumerate(pages):
        page.save(f'documents/{pdf_uuid}/out{count}.jpg', 'JPEG')
