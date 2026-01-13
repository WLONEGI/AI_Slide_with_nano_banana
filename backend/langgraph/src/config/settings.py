from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Final

class Settings(BaseSettings):
    """
    Application Settings.
    
    Values can be overridden by environment variables.
    Example: MAX_RETRIES=5 in .env file.
    """
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Retry limits
    MAX_RETRIES: int = 3
    MAX_REPLANNING: int = 3
    
    # Concurrency limits
    VISUALIZER_CONCURRENCY: int = 5
    
    # Recursion limits
    RECURSION_LIMIT_WORKFLOW: int = 50
    RECURSION_LIMIT_RESEARCHER: int = 7

    # Service limits
    MAX_COORD_CACHE_SIZE: int = 2
    
    # Project Info
    PROJECT_NAME: str = "Lang-Manus"
    VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Response Template (Formatted string, not pure config but kept for consistency)
    RESPONSE_FORMAT: str = "Response from {role}:\n\n<response>\n{content}\n</response>\n\n*Step completed.*"

settings = Settings()
