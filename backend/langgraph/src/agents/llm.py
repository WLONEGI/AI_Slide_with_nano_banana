from functools import lru_cache
from typing import Optional, Union, Dict, Any
import logging
import os

from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek
from langchain_google_genai import ChatGoogleGenerativeAI
# google-cloud-aiplatform / langchain-google-vertexai REMOVED

from src.config.env import (
    BASIC_MODEL,
    BASIC_BASE_URL,
    BASIC_API_KEY,
    REASONING_MODEL,
    REASONING_BASE_URL,
    REASONING_API_KEY,
    VL_MODEL,
    VL_BASE_URL,
    VL_API_KEY,
    VERTEX_PROJECT_ID,
    VERTEX_LOCATION,
    HIGH_REASONING_MODEL,
    HIGH_REASONING_BASE_URL,
    HIGH_REASONING_API_KEY,
)

logger = logging.getLogger(__name__)

def create_openai_llm(
    model: str, base_url: str | None = None, api_key: str | None = None, temperature: float = 0.0
) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        base_url=base_url,
        api_key=api_key,
        temperature=temperature,
    )

def create_deepseek_llm(
    model: str, base_url: str | None = None, api_key: str | None = None, temperature: float = 0.0
) -> ChatDeepSeek:
    return ChatDeepSeek(
        model=model,
        base_url=base_url,
        api_key=api_key,
        temperature=temperature,
    )

def create_gemini_llm(
    model: str, 
    api_key: str | None = None, 
    project: str | None = None,
    location: str | None = None,
    temperature: float = 0.0
) -> ChatGoogleGenerativeAI:
    """
    Create a ChatGoogleGenerativeAI instance.
    Supports both AI Studio (API Key) and Vertex AI (ADC/Project).
    The new langchain-google-genai with google-genai SDK handles both.
    """
    
    # If using Vertex AI (Project provided or no API Key), ensure Env vars are set
    # as google-genai client often looks for them.
    if project:
        os.environ["GOOGLE_CLOUD_PROJECT"] = project
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
    if location:
        os.environ["GOOGLE_CLOUD_LOCATION"] = location
    
    # If API key is provided, it will be used (AI Studio).
    # If not, it will fall back to ADC (Vertex AI).
    
    kwargs = {
        "model": model,
        "temperature": temperature,
    }
    if api_key:
        kwargs["google_api_key"] = api_key
    elif location:
        # Explicitly pass location for Vertex AI to prevent defaulting to the runtime region
        kwargs["location"] = location
    
    return ChatGoogleGenerativeAI(**kwargs)



@lru_cache(maxsize=10)
def get_llm_by_type(llm_type: str) -> Union[ChatOpenAI, ChatDeepSeek, ChatGoogleGenerativeAI]:
    """
    Factory function to get an LLM instance based on the type defined in config.
    """
    if llm_type == "reasoning":
        model = REASONING_MODEL
        base_url = REASONING_BASE_URL
        api_key = REASONING_API_KEY
    elif llm_type == "vision":
        model = VL_MODEL
        base_url = VL_BASE_URL
        api_key = VL_API_KEY
    elif llm_type == "high_reasoning":
        model = HIGH_REASONING_MODEL
        base_url = HIGH_REASONING_BASE_URL
        api_key = HIGH_REASONING_API_KEY
    else:  # basic / default
        model = BASIC_MODEL
        base_url = BASIC_BASE_URL
        api_key = BASIC_API_KEY

    if not model:
        raise ValueError(f"No model configured for type '{llm_type}'")

    model_lower = model.lower()

    if "gpt" in model_lower:
        return create_openai_llm(model, base_url, api_key)
    elif "deepseek" in model_lower:
        return create_deepseek_llm(model, base_url, api_key)
    
    if "gemini" in model_lower:
        # Unified Gemini Logic using ONLY Google Gen AI SDK
        logger.info(f"DEBUG: Checking Auth for {llm_type}. ProjectID: {'SET' if VERTEX_PROJECT_ID else 'None'}, APIKey: {'SET' if api_key else 'None'}")
        
        # PRIORITIZE Vertex AI if Project ID is available (User Request)
        if VERTEX_PROJECT_ID:
            # STRICT RULE: Do NOT use ChatVertexAI. Use ChatGoogleGenerativeAI with Vertex AI Auth.
            logger.info(f"Using Vertex AI via ChatGoogleGenerativeAI for {llm_type} (model: {model})")
            
            # For Vertex AI with google-genai SDK, we typically set env vars or rely on ADC.
            # ChatGoogleGenerativeAI uses google-genai SDK internally now (v2+).
            # We explicitly pass None for api_key to ensure it uses ADC/Project.
            return create_gemini_llm(
                model=model,
                api_key=None,  # Force ADC / Vertex Mode
                project=VERTEX_PROJECT_ID,
                location=VERTEX_LOCATION or "asia-northeast1",
                temperature=0.0
            )
        # Fallback to API Key (AI Studio)
        elif api_key:
            logger.info(f"Using Google GenAI (API Key) for {llm_type} (model: {model})")
            return create_gemini_llm(model=model, api_key=api_key)
            
    else:
        # Default fallback to OpenAI-compatible
        return create_openai_llm(model, base_url, api_key)

# Pre-initialize common instances
reasoning_llm = get_llm_by_type("reasoning")
basic_llm = get_llm_by_type("basic")
vl_llm = get_llm_by_type("vision")

