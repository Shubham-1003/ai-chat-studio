import streamlit as st
import fitz  # PyMuPDF
from docx import Document
import json
import nbformat
from zipfile import ZipFile
from PIL import Image
import io
import base64
import os

# Consider adding OCR libraries if needed (e.g., pytesseract, easyocr)
# import pytesseract
# from pdf2image import convert_from_bytes # If processing PDF images


def parse_pdf(file_content: bytes) -> str:
    """Extracts text content from a PDF file."""
    text = ""
    try:
        with fitz.open(stream=file_content, filetype="pdf") as doc:
            for page in doc:
                text += page.get_text()
        # Optional: Add image extraction/OCR here if needed
        # images = []
        # for page_num in range(len(doc)):
        #     page = doc.load_page(page_num)
        #     image_list = page.get_images(full=True)
        #     for img_index, img in enumerate(image_list):
        #         xref = img[0]
        #         base_image = doc.extract_image(xref)
        #         image_bytes = base_image["image"]
        #         # Process image_bytes (e.g., OCR)
    except Exception as e:
        st.error(f"Error parsing PDF: {e}")
        return "Error parsing PDF."
    return text

def parse_docx(file_content: bytes) -> str:
    """Extracts text content from a DOCX file."""
    text = ""
    try:
        doc = Document(io.BytesIO(file_content))
        for para in doc.paragraphs:
            text += para.text + "\n"
        # Optional: Add table extraction logic
    except Exception as e:
        st.error(f"Error parsing DOCX: {e}")
        return "Error parsing DOCX."
    return text

def parse_txt(file_content: bytes) -> str:
    """Reads content from a TXT file."""
    try:
        return file_content.decode('utf-8', errors='ignore')
    except Exception as e:
        st.error(f"Error parsing TXT: {e}")
        return "Error parsing TXT."

def parse_ipynb(file_content: bytes) -> str:
    """Extracts code and markdown content from a Jupyter Notebook."""
    content = ""
    try:
        notebook_str = file_content.decode('utf-8', errors='ignore')
        nb = nbformat.reads(notebook_str, as_version=4)
        content += f"# Notebook: {nb.metadata.get('title', 'Untitled')}\n\n"
        for cell in nb.cells:
            if cell.cell_type == 'markdown':
                content += f"## Markdown Cell:\n{cell.source}\n\n"
            elif cell.cell_type == 'code':
                content += f"## Code Cell:\n```python\n{cell.source}\n```\n"
                # Optional: Include outputs if needed
                # if 'outputs' in cell:
                #     for output in cell.outputs:
                #         if 'text' in output:
                #             content += f"### Output:\n{output['text']}\n"
                #         elif 'data' in output and 'text/plain' in output['data']:
                #              content += f"### Output:\n{output['data']['text/plain']}\n"
        return content
    except Exception as e:
        st.error(f"Error parsing IPYNB: {e}")
        return "Error parsing IPYNB."

def parse_image(file_content: bytes) -> tuple[str, Image.Image | None]:
    """Loads an image file and returns description and Pillow Image object."""
    try:
        img = Image.open(io.BytesIO(file_content))
        description = f"Image loaded: {img.format} format, {img.size} pixels."
        # Placeholder for potential OCR or other image analysis
        # ocr_text = pytesseract.image_to_string(img) # Example using pytesseract
        # description += f"\nOCR Text (if applicable): {ocr_text}"
        return description, img # Return description and the image object
    except Exception as e:
        st.error(f"Error parsing Image: {e}")
        return "Error parsing Image.", None

def parse_zip(file_content: bytes, filename: str) -> str:
    """Lists contents of a ZIP file (does not extract recursively by default)."""
    content_summary = f"Contents of ZIP file '{filename}':\n"
    try:
        with ZipFile(io.BytesIO(file_content)) as zf:
            for file_info in zf.infolist():
                content_summary += f"- {file_info.filename} ({file_info.file_size} bytes)\n"
                # TODO: Optionally add logic here to extract specific file types
                # from within the zip and parse them if needed.
                # This can get complex quickly.
    except Exception as e:
        st.error(f"Error parsing ZIP: {e}")
        return "Error parsing ZIP."
    return content_summary

# --- Main Processing Function ---

def process_uploaded_file(uploaded_file):
    """
    Processes an uploaded file based on its type and returns its content or representation.
    Returns a tuple: (content_representation, file_metadata)
    content_representation can be text, description string, or potentially image data
    file_metadata contains info like name, type, and potentially the raw image object
    """
    file_content = uploaded_file.getvalue()
    file_type = uploaded_file.type
    file_name = uploaded_file.name
    content = None
    image_obj = None # To store PIL Image if it's an image file

    st.info(f"Processing {file_name} ({file_type})...")

    if file_type == "application/pdf":
        content = parse_pdf(file_content)
    elif file_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"]:
        content = parse_docx(file_content)
    elif file_type == "text/plain":
        content = parse_txt(file_content)
    elif file_type in ["image/jpeg", "image/png"]:
        content, image_obj = parse_image(file_content) # Gets description and Image obj
    elif file_name.endswith(".ipynb"): # Streamlit might not always detect type correctly
         content = parse_ipynb(file_content)
    elif file_type == "application/zip" or file_name.endswith(".zip"):
        content = parse_zip(file_content, file_name)
    else:
        content = f"Unsupported file type: {file_type}. Cannot process."
        st.warning(content)

    file_metadata = {
        "name": file_name,
        "type": file_type,
        "size": uploaded_file.size,
        "image_obj": image_obj, # Store the image object if available
    }

    st.success(f"Finished processing {file_name}.")
    return content, file_metadata


# --- File Generation / Download ---

def generate_download_link(content: str | bytes, filename: str, link_text: str) -> None:
    """Generates a Streamlit download button for text or bytes content."""
    if isinstance(content, str):
        data = content.encode('utf-8')
        mime = "text/plain"
    else:
        data = content
        # Try to guess mime type based on extension (very basic)
        if filename.endswith(".pdf"):
            mime = "application/pdf"
        elif filename.endswith(".docx"):
            mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif filename.endswith(".txt"):
             mime = "text/plain"
        elif filename.endswith(".ipynb"):
             mime = "application/x-ipynb+json"
        elif filename.endswith(".png"):
             mime = "image/png"
        elif filename.endswith(".jpg") or filename.endswith(".jpeg"):
             mime = "image/jpeg"
        else:
            mime = "application/octet-stream" # Default binary type

    st.download_button(
        label=link_text,
        data=data,
        file_name=filename,
        mime=mime,
    )

# Example usage within the app for generating a download link:
# if "generated_file_content" in response_data:
#     generate_download_link(
#         response_data["generated_file_content"],
#         response_data["generated_filename"],
#         f"Download {response_data['generated_filename']}"
#     )