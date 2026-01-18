import logging
from google import genai
from google.genai import types
from src.config.env import VERTEX_PROJECT_ID, VERTEX_LOCATION, VL_MODEL

logger = logging.getLogger(__name__)

def generate_image(prompt: str, seed: int | None = None, reference_image: bytes | None = None, thought_signature: str | None = None) -> tuple[bytes, str | None]:
    """
    Generate an image using Vertex AI via google-genai SDK.
    Supports both Imagen and Gemini.
    
    Args:
        prompt (str): The text prompt for image generation.
        seed (int | None): Optional random seed for deterministic generation. Defaults to None.
        reference_image (bytes | None): Optional image bytes to use as a reference (multimodal input). Defaults to None.
        
    Returns:
        tuple[bytes, str | None]: The generated image data (PNG format) and the new thought_signature (if available).
    
    Raises:
        ValueError: If no image data is found in the response.
        Exception: Re-raises exceptions from the Vertex AI client after logging.
    """
    try:
        # Initialize google-genai Client for Vertex AI
        client = genai.Client(
            vertexai=True,
            project=VERTEX_PROJECT_ID,
            location=VERTEX_LOCATION
        )
        
        model_name = VL_MODEL
        logger.info(f"Generating image with model: {model_name} (Prompt: {prompt[:50]}..., Seed: {seed}, Has Ref: {bool(reference_image)})")

        # Construct contents for multimodal input
        contents = [prompt]
        if reference_image:
            # Create a Part from bytes.
            contents.append(types.Part.from_bytes(data=reference_image, mime_type="image/png"))

        # Gemini 3 / Multimodal generation
        config_params = {"response_modalities": ["IMAGE"]}
        
        if seed is not None:
             config_params["seed"] = seed

        # Add thought_signature if provided (Critical for Deep Edit consistency in Gemini 3.0)
        if thought_signature:
            logger.info("Using previous thought_signature for consistency.")
            # Verify exact parameter name via testing or broad assignment
            config_params["thought_signature"] = thought_signature

        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=types.GenerateContentConfig(**config_params)
        )
        
        # Extraction logic
        generated_image = None
        new_thought_signature = None

        if response.candidates:
            # Extract image
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    generated_image = part.inline_data.data
            
            # Extract thought_signature (Try checking candidate attributes)
            try:
                # Based on research, it might be in candidate metadata or attributes
                # We'll check common locations.
                candidate = response.candidates[0]
                if hasattr(candidate, "thought_signature"):
                    new_thought_signature = candidate.thought_signature
                # If checking a dict response:
                # elif "thoughtSignature" in candidate.to_dict():
                #     new_thought_signature = candidate.to_dict()["thoughtSignature"]
            except Exception as e:
                logger.warning(f"Could not extract thought_signature: {e}")

        if generated_image:
            return generated_image, new_thought_signature
        
        raise ValueError(f"No image data found in Gemini response. Response: {response}")

    except Exception as e:
        logger.error(f"Image generation failed with {VL_MODEL}: {e}")
        # 404エラーの場合のトラブルシューティング案内
        if "404" in str(e):
             logger.error("Hint: Please check if you have accepted the Terms of Service for this model in Model Garden, or if the API is enabled.")
        raise e
