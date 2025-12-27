
from .vertex_wrapper import get_gemini
from vertexai.generative_models import Part, GenerationResponse
import logging
import json
from typing import Tuple, Dict, Any, List
import random

logger = logging.getLogger(__name__)

# Constants
MIN_TEXT_BLOCKS = 1
MIN_CONFIDENCE = 0.85
MAX_ILLEGIBLE_BLOCKS = 1
MAX_SAMPLE_IMAGES = 4


def _sample_representative_images(images: List[bytes]) -> List[bytes]:
    """
    Samples representative images for consistency check.

    Args:
        images (List[bytes]): All available images.

    Returns:
        List[bytes]: Sampled images (first, last, plus 2 random middle).
    """
    if len(images) <= MAX_SAMPLE_IMAGES:
        return images
    
    # Always include first and last
    sample_indices = [0, len(images) - 1]
    
    # Add up to 2 random middle images
    middle_indices = list(range(1, len(images) - 1))
    additional_count = min(2, len(middle_indices))
    sample_indices.extend(random.sample(middle_indices, additional_count))
    
    return [images[i] for i in sorted(sample_indices)]


def _evaluate_quality_metrics(quality_result: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """
    Evaluates quality metrics from the analysis result.

    Args:
        quality_result (Dict[str, Any]): The parsed quality analysis.

    Returns:
        Tuple[bool, Dict[str, Any]]: (is_passed, result_details)
    """
    text_block_count = quality_result.get("text_block_count")
    average_confidence = quality_result.get("average_confidence")
    illegible_block_count = quality_result.get("illegible_block_count")

    # Guard: Check for missing fields
    if text_block_count is None or average_confidence is None or illegible_block_count is None:
        logger.warning("Quality Gate result missing fields. Treating as NG.")
        return False, {"reason": "missing_fields"}

    is_passed = (
        int(text_block_count) >= MIN_TEXT_BLOCKS
        and float(average_confidence) >= MIN_CONFIDENCE
        and int(illegible_block_count) <= MAX_ILLEGIBLE_BLOCKS
    )
    return is_passed, quality_result


async def check_quality(image_bytes: bytes) -> Tuple[bool, Dict[str, Any]]:
    """
    Checks if the text in the slide image is legible.

    Args:
        image_bytes (bytes): The image data.

    Returns:
        Tuple[bool, Dict[str, Any]]: A tuple containing (is_passed, result_details).
    """
    model = get_gemini()
    
    prompt = """
    Analyze this slide image for text legibility.
    Output strictly VALID JSON with the following format:
    {
      "text_block_count": <int>,
      "average_confidence": <float, 0.0-1.0>,
      "illegible_block_count": <int>,
      "overall_judgement": "OK" or "NG"
    }
    Criteria for OK:
    1. At least 1 text block detected.
    2. Average confidence >= 0.85.
    3. Illegible blocks <= 1.
    If the slide has NO text intentionally (e.g. just an image), check if it looks like a valid visual slide.
    """
    
    try:
        image_part = Part.from_data(data=image_bytes, mime_type="image/png")
        
        response: GenerationResponse = model.generate_content(
            [image_part, prompt],
            generation_config={"response_mime_type": "application/json"}
        )
        
        quality_result: Dict[str, Any] = json.loads(response.text)
        logger.info(f"Quality Gate Result: {quality_result}")

        return _evaluate_quality_metrics(quality_result)
        
    except Exception as e:
        logger.error(f"Quality Gate Error: {e}")
        return False, {"reason": str(e)}


async def check_style_consistency(images: List[bytes], style_description: str) -> Dict[str, Any]:
    """
    Checks if a batch of images share a consistent visual style.

    Args:
        images (List[bytes]): List of image data.
        style_description (str): Description of the intended style.

    Returns:
        Dict[str, Any]: A dict with consistency_score and feedback.
    """
    model = get_gemini()
    
    sampled_images = _sample_representative_images(images)
    
    prompt = f"""
    Act as a strictly critical Design Director.
    Analyze these {len(sampled_images)} slide images. verify if they share a consistent visual identity (Color Palette, Typography weight, Illustration style).
    Context: The user wanted style "{style_description}".
    
    Output strictly VALID JSON:
    {{
      "consistency_score": <int 0-100>,
      "is_consistent": <bool (true if score > 70)>,
      "feedback": "<concise text explaining the verdict>"
    }}
    """
    
    content_parts: List[Any] = [
        Part.from_data(data=img_bytes, mime_type="image/png")
        for img_bytes in sampled_images
    ]
    content_parts.append(prompt)
    
    try:
        response: GenerationResponse = model.generate_content(
            content_parts,
            generation_config={"response_mime_type": "application/json"}
        )
        consistency_result: Dict[str, Any] = json.loads(response.text)
        logger.info(f"Style Consistency Check: {consistency_result}")
        return consistency_result
    except Exception as e:
        logger.error(f"Consistency Check Error: {e}")
        return {"consistency_score": 0, "is_consistent": False, "feedback": str(e)}
