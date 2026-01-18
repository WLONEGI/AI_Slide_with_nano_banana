import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

def get_env_var(key: str, default: str | None = None) -> str | None:
    value = os.getenv(key, default)
    if value:
        return value.strip()
    
    if default is None:
        logger.debug(f"Environment variable {key} is not set.")
    return value

# Reasoning LLM configuration (for complex reasoning tasks)
REASONING_MODEL = get_env_var("REASONING_MODEL", "gemini-2.0-flash-thinking-exp-1219")
REASONING_BASE_URL = get_env_var("REASONING_BASE_URL")
REASONING_API_KEY = get_env_var("REASONING_API_KEY")

# Non-reasoning LLM configuration (for straightforward tasks)
BASIC_MODEL = get_env_var("BASIC_MODEL", "gemini-1.5-flash-002")
BASIC_BASE_URL = get_env_var("BASIC_BASE_URL")
BASIC_API_KEY = get_env_var("BASIC_API_KEY")

# Vision-language LLM configuration (for tasks requiring visual understanding)
VL_MODEL = get_env_var("VL_MODEL", "gemini-3-pro-image-preview")
VL_BASE_URL = get_env_var("VL_BASE_URL")
VL_API_KEY = get_env_var("VL_API_KEY")

# Specialized Agent Models (High Reasoning)
HIGH_REASONING_MODEL = get_env_var("HIGH_REASONING_MODEL", "gemini-2.0-flash-thinking-exp-1219")
HIGH_REASONING_BASE_URL = get_env_var("HIGH_REASONING_BASE_URL")
HIGH_REASONING_API_KEY = get_env_var("HIGH_REASONING_API_KEY")


# Vertex AI configuration
VERTEX_PROJECT_ID = get_env_var("VERTEX_PROJECT_ID")
VERTEX_LOCATION = get_env_var("VERTEX_LOCATION")

# Chrome Instance configuration
CHROME_INSTANCE_PATH = get_env_var("CHROME_INSTANCE_PATH")

# Utils configuration
PPTX_RENDER_TIMEOUT = int(get_env_var("PPTX_RENDER_TIMEOUT", "60"))

# Storage & Persistence configuration
GCS_BUCKET_NAME = get_env_var("GCS_BUCKET_NAME")
POSTGRES_DB_URI = get_env_var("POSTGRES_DB_URI")

if VERTEX_LOCATION and VERTEX_LOCATION.startswith("-"):
    logger.warning(f"⚠️ VERTEX_LOCATION starts with a hyphen ('{VERTEX_LOCATION}'). This is likely a typo in your .env file.")

