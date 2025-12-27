
import vertexai
from vertexai.generative_models import GenerativeModel
import os
import logging
from google import genai
from typing import Optional, Any
from .mocks import MockGenerativeModel, MockImageGenerationModel

logger = logging.getLogger(__name__)

# Default to a placeholder if not set, but typical ADC might need explicit init if project not found.
PROJECT_ID: Optional[str] = os.getenv("GOOGLE_CLOUD_PROJECT", "spell-480408")
LOCATION: Optional[str] = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
APP_ENV: str = os.getenv("APP_ENV", "prod") # Default to prod for real AI

# Note: GEMINI_API_KEY is specifically for the Google Gen AI SDK (Imagen), 
# whereas Vertex AI (Gemini) uses Google Cloud Application Default Credentials (ADC).
GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY") 
GEMINI_IMAGE_MODEL: str = os.getenv("GEMINI_IMAGE_MODEL", "gemini-3-pro-image-preview")

_initialized: bool = False

def ensure_init() -> None:
    """
    Initializes Vertex AI if strictly necessary and not in dev mode.
    """
    global _initialized
    if APP_ENV == "dev":
        logger.info("Running in DEV mode. Vertex AI init skipped.")
        return

    if not _initialized:
        # If PROJECT_ID is None, vertexai.init might infer from ADC or metadata server
        try:
            vertexai.init(project=PROJECT_ID, location=LOCATION)
            _initialized = True
            logger.info(f"Vertex AI initialized with project={PROJECT_ID}, location={LOCATION}")
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI: {e}")
            raise

def get_gemini() -> Any: # Returns GenerativeModel or Mock
    """
    Returns an instance of the Gemini generative model or a mock.

    Returns:
        Any: GenerativeModel or MockGenerativeModel
    """
    if APP_ENV == "dev":
        return MockGenerativeModel()
    ensure_init()
    # User requested gemini-2.5-flash.
    try:
        return GenerativeModel("gemini-2.5-flash")
    except Exception as e:
         logger.warning(f"Could not load gemini-2.5-flash. Error: {e}")
         raise e

def get_imagen() -> Any: # Returns genai.Client or Mock
    """
    Returns an instance of the Imagen client or a mock.

    Returns:
        Any: genai.Client or MockImageGenerationModel
    """
    if APP_ENV == "dev":
        return MockImageGenerationModel()
    
    # [Ultrahinking] Logic: If user hasn't provided GEMINI_API_KEY but wants logic/text AI (APP_ENV=prod), 
    # we shouldn't crash on Image Generation. Fallback to Mock for Images only.
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not found. Falling back to MockImageGenerationModel for Image Generation.")
        return MockImageGenerationModel()
        
    return genai.Client(api_key=GEMINI_API_KEY)

def get_image_model_name() -> str:
    """
    Returns the configured image model name.

    Returns:
        str: Model name.
    """
    return GEMINI_IMAGE_MODEL

async def call_gemini_flash(prompt: str) -> str:
    """
    Call Gemini Flash model with a text prompt and return the response text.
    Used by refiner.py for the Refiner Agent.

    Args:
        prompt (str): The prompt to send to the model.

    Returns:
        str: The generated text response.
    """
    model = get_gemini()
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"call_gemini_flash error: {e}")
        raise
