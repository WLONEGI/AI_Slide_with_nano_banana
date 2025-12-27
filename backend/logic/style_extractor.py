
from .models import StyleDef, LayoutDef
from .vertex_wrapper import get_gemini
from vertexai.generative_models import Part, GenerationResponse
import json
import logging
import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import Optional, List, Any

logger = logging.getLogger(__name__)

PPTX_MIME: str = "application/vnd.openxmlformats-officedocument.presentationml.presentation"

def _convert_pptx_to_pdf_bytes(file_bytes: bytes) -> bytes:
    """
    Converts PPTX file bytes to PDF bytes using LibreOffice.

    Args:
        file_bytes (bytes): The content of the PPTX file.

    Returns:
        bytes: The content of the converted PDF file.

    Raises:
        FileNotFoundError: If LibreOffice is not installed or PDF generation fails.
        subprocess.CalledProcessError: If the conversion process fails.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        pptx_path = tmp_path / "input.pptx"
        pptx_path.write_bytes(file_bytes)

        binary: Optional[str] = shutil.which("libreoffice") or shutil.which("soffice")
        if not binary:
            logger.error("libreoffice/soffice is not installed or not in PATH.")
            raise FileNotFoundError("libreoffice/soffice not found")

        try:
            subprocess.run(
                [
                    binary,
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(tmp_path),
                    str(pptx_path),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=60,
            )
        except FileNotFoundError as e:
            logger.error("libreoffice is not installed or not in PATH.")
            raise e
        except subprocess.CalledProcessError as e:
            logger.error(f"PPTX conversion failed: {e.stderr.decode('utf-8', errors='ignore')}")
            raise

        pdf_path = pptx_path.with_suffix(".pdf")
        if not pdf_path.exists():
            pdf_files = list(tmp_path.glob("*.pdf"))
            if not pdf_files:
                raise FileNotFoundError("PPTX conversion failed: PDF not generated.")
            pdf_path = pdf_files[0]

        return pdf_path.read_bytes()

async def extract_style_from_text(description: str, file_bytes: Optional[bytes] = None, mime_type: Optional[str] = None) -> StyleDef:
    """
    Extracts style definition from a text description and/or reference file.

    Args:
        description (str): Text description of the desired style.
        file_bytes (Optional[bytes]): Content of a style reference file (PDF/Image/PPTX).
        mime_type (Optional[str]): MIME type of the file.

    Returns:
        StyleDef: The extracted style definition.
    """
    # If description is empty, use default
    if not description and not file_bytes:
        description = "Modern, clean, minimal business presentation."
        
    model = get_gemini()
    
    prompt_text: str = f"""
    You are a professional Creative Director and Prompt Engineer for high-end presentation design.
    Analyze the provided input (description and/or file) and define a consistent visual style for a slide deck.
    
    Description: "{description}"
    
    Your goal is to output a JSON object that strictly follows the `StyleDef` schema, including a `global_prompt` that will be used by Imagen 3 to ensure design consistency across all slides.
    
    The `global_prompt` should include:
    1. **Overall Aesthetic**: (e.g., Minimalist, Bauhaus, Futuro-Retro, Corporate Swiss)
    2. **Color Palette**: Specify primary, secondary, and background colors.
    3. **Typography Hints**: Describe font characteristics (e.g., bold sans-serif, elegant serif).
    4. **Lighting & Mood**: (e.g., Studio lighting, soft shadows, vibrant, muted).
    5. **Common Elements**: Persistent visual marks (e.g., logo placement, geometric frame).
    
    The `layouts` should be a selection of exactly 3 relevant layout patterns from the following types, customized for this style:
    - `title`: Central impact, high-contrast title placement.
    - `content_left`: Text/Bulleted list on the left, visual element on the right.
    - `visual_center`: Large central graphic or chart area with minor captioning.
    - `split_horizontal`: High-impact top visual, detailed data/text bottom.
    
    Output Format (JSON strictly):
    {{
        "global_prompt": "A detailed style guide for Imagen 3... [aesthetic, colors, typography, mood]",
        "layouts": [
            {{ "layout_id": "title", "visual_description": "Compositional guidance for title slides in this style..." }},
            {{ "layout_id": "content_left", "visual_description": "Compositional guidance for content slides..." }},
            {{ "layout_id": "visual_center", "visual_description": "Compositional guidance for visual-heavy slides..." }}
        ]
    }}
    """
    
    parts: List[Any] = [prompt_text]
    if file_bytes and mime_type:
        if mime_type == PPTX_MIME:
            file_bytes = _convert_pptx_to_pdf_bytes(file_bytes)
            mime_type = "application/pdf"
        # Gemini accepts PDF and Images.
        try:
            part = Part.from_data(data=file_bytes, mime_type=mime_type)
            parts.append(part)
        except Exception as e:
            logger.warning(f"Could not create Part from file: {e}")
            
    try:
        response: GenerationResponse = model.generate_content(parts, generation_config={"response_mime_type": "application/json"})
        data = json.loads(response.text)
        # Parse layouts manually to ensure list
        layouts = [LayoutDef(**l) for l in data.get("layouts", [])]
        return StyleDef(global_prompt=data.get("global_prompt", ""), layouts=layouts)
    except Exception as e:
        logger.error(f"Error extracting style: {e}")
        # Default fallback
        return StyleDef(
            global_prompt="Professional, clean, white background, blue accents, photorealistic 8k",
            layouts=[LayoutDef(layout_id="default", visual_description="simple centered")]
        )
