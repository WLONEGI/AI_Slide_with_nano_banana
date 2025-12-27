
from .vertex_wrapper import get_imagen, get_image_model_name
from .models import Slide, StyleDef
import logging
from google.genai import types
from typing import Optional, List, Any

logger = logging.getLogger(__name__)

def _build_prompt(slide: Slide, style_def: Optional[StyleDef]) -> str:
    """
    Builds the image generation prompt by combining slide visual prompt and style context.

    Args:
        slide (Slide): The slide object.
        style_def (Optional[StyleDef]): The style definition.

    Returns:
        str: The constructed prompt.
    """
    parts: List[str] = []
    if style_def:
        if style_def.global_prompt:
            parts.append(style_def.global_prompt.strip())
        if style_def.layouts:
            matched = next((l for l in style_def.layouts if l.layout_id == slide.layout_id), None)
            if matched and matched.visual_description:
                parts.append(matched.visual_description.strip())
    if slide.visual_prompt:
        parts.append(slide.visual_prompt.strip())
    return ". ".join(p.rstrip(".") for p in parts if p)

def _extract_image_bytes(response: Any) -> bytes:
    """
    Extracts image bytes from the generation response.

    Args:
        response (Any): The response object from the generative model.

    Returns:
        bytes: The image data.

    Raises:
        ValueError: If no image bytes are found in the response.
    """
    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            inline = getattr(part, "inline_data", None)
            if inline and getattr(inline, "data", None):
                return inline.data
    raise ValueError("No image bytes found in Gemini response.")

def generate_slide_image(slide: Slide, style_def: Optional[StyleDef] = None) -> bytes:
    """
    Generates an image for a slide using Imagen.

    Args:
        slide (Slide): The slide to generate an image for.
        style_def (Optional[StyleDef]): The design style to apply.

    Returns:
        bytes: The generated image data.
    """
    try:
        model = get_imagen()

        prompt: str = _build_prompt(slide, style_def)
        logger.info(f"Generating image for slide {slide.slide_id} with prompt: {prompt}")

        if hasattr(model, "generate_images"):
            response = model.generate_images(
                prompt=prompt,
                number_of_images=1,
                aspect_ratio="16:9",
            )
            image_obj = response[0]
            if hasattr(image_obj, "_image_bytes"):
                return image_obj._image_bytes
            raise ValueError("Could not extract bytes from GeneratedImage")


        response = model.models.generate_content(
            model=get_image_model_name(),
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio="16:9",
                    image_size="2K",
                )
            ),
        )
        return _extract_image_bytes(response)
            
    except Exception as e:
        logger.error(f"Error generating image: {e}")
        raise

def generate_inpainted_image(
    base_image_bytes: bytes,
    mask_image_bytes: bytes,
    prompt: str,
    style_def: Optional[StyleDef] = None
) -> bytes:
    """
    Generates an edited (inpainted) image based on a prompt and mask.

    Args:
        base_image_bytes (bytes): The original image.
        mask_image_bytes (bytes): The mask image indicating area to edit.
        prompt (str): The editing instruction or description.
        style_def (Optional[StyleDef]): The style context.

    Returns:
        bytes: The generated image data.
    """
    try:
        model = get_imagen()
        
        # Build prompt similarly or use just the instruction? 
        # For inpainting, usually just the object description or modification instruction is needed.
        # But keeping style context is good.
        full_prompt: str = prompt
        if style_def and style_def.global_prompt:
            full_prompt = f"{style_def.global_prompt}. {prompt}"

        logger.info(f"Generating inpainted image with prompt: {full_prompt}")

        # Construct OneImage input for editing (assuming GenAI SDK usage)
        # Note: The exact method for edit might differ. 
        # Using standard generate_images with reference image and mask for now if supported,
        # or assuming `edit_images` if that exists in the SDK version used.
        # The prompt mentioned "Gemini 3 Pro Image (Imagen 3) Inpainting (Edit Mode)".
        # Typically this is done by passing the image and mask in contents.
        
        # Checking if using genai.Client (Google Gen AI SDK)
        if hasattr(model, "models"):
            # GenAI SDK 0.1+
            # Logic for editing often involves passing the image and mask as parts
            from google.genai import types
            
            # Create image objects
            # Need to convert bytes to Image object recognizable by the SDK if needed, 
            # or just pass as Part with inline data.
            
            b_image = types.Part.from_bytes(data=base_image_bytes, mime_type="image/png")
            m_image = types.Part.from_bytes(data=mask_image_bytes, mime_type="image/png")
            
            # For Imagen 3 editing, we might need to use a specific edit call or just generate_content with images.
            # Assuming generate_content handles it with proper model capabilities.
            
            response = model.models.generate_content(
                model=get_image_model_name(), # Ensure this model supports editing
                contents=[
                    full_prompt, 
                    b_image, 
                    m_image 
                ],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                     # Some APIs require explicitly setting mode="edit" or similar, 
                     # but often implicit by presence of mask.
                ),
            )
            return _extract_image_bytes(response)
        
        else:
            # Mock or vertexai SDK legacy
            raise NotImplementedError("Inpainting not supported on this backend configuration.")

    except Exception as e:
        logger.error(f"Error generating inpainted image: {e}")
        raise
