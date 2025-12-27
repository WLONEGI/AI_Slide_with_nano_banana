
import img2pdf
from typing import List
import logging

logger = logging.getLogger(__name__)

def assemble_pdf(image_bytes_list: List[bytes]) -> bytes:
    """
    Assembles a list of image bytes into a single PDF file.

    Args:
        image_bytes_list (List[bytes]): A list of image data in bytes format.

    Returns:
        bytes: The generated PDF data in bytes.

    Raises:
        Exception: If the PDF conversion fails.
    """
    try:
        pdf_bytes: bytes = img2pdf.convert(image_bytes_list)
        return pdf_bytes
    except Exception as e:
        logger.error(f"Error assembling PDF: {e}")
        raise
