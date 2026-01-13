import logging
from google import genai
from google.genai import types
from src.config.env import VERTEX_PROJECT_ID, VERTEX_LOCATION, VL_MODEL

logger = logging.getLogger(__name__)

def generate_image(prompt: str, seed: int | None = None, reference_image: bytes | None = None) -> bytes:
    """
    Generate an image using Vertex AI via google-genai SDK.
    Supports both Imagen and Gemini.
    
    Args:
        prompt (str): The text prompt for image generation.
        seed (int | None): Optional random seed for deterministic generation. Defaults to None.
        reference_image (bytes | None): Optional image bytes to use as a reference (multimodal input). Defaults to None.
        
    Returns:
        bytes: The generated image data (PNG format).
    
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
            # Create a Part from bytes. Assuming generic image type or detecting?
            # google-genai SDK handles Part.from_bytes or dict structure.
            # Let's use the explicit Part object if available in types, or simple dict structure if supported.
            # Checking imports: from google.genai import types.
            # Best practice: use types.Part.from_bytes if available, or construct Part.
            contents.append(types.Part.from_bytes(data=reference_image, mime_type="image/png"))

        # Gemini 3 / Multimodal generation
        # Use generate_content
        
        config_params = {"response_modalities": ["IMAGE"]}
        # Note: 'seed' parameter location depends on SDK version. 
        # Typically distinct from 'random_seed' in some APIs, but for GenAI usually 'seed' or inside config.
        # Checking implementation plan assumption: "Pass seed to GenerateContentConfig".
        # We will map it to 'seed' if supported, or check 'random_seed'.
        # For now assuming 'seed' as per plan.
        if seed is not None:
             config_params["seed"] = seed

        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=types.GenerateContentConfig(**config_params)
        )
        
        # Extraction logic: Look for inline data in parts
        if response.candidates:
            for part in response.candidates[0].content.parts:
                # inline_data に画像が含まれているか確認
                if part.inline_data and part.inline_data.data:
                    return part.inline_data.data
        
        raise ValueError(f"No image data found in Gemini response. Response: {response}")

    except Exception as e:
        logger.error(f"Image generation failed with {VL_MODEL}: {e}")
        # 404エラーの場合のトラブルシューティング案内
        if "404" in str(e):
             logger.error("Hint: Please check if you have accepted the Terms of Service for this model in Model Garden, or if the API is enabled.")
        raise e
