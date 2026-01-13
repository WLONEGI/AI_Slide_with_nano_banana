
import pytest
import os
import sys
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# API Key Fallback Logic for Testing
# Check if specific keys are missing but GOOGLE_API_KEY exists
if os.getenv("GOOGLE_API_KEY"):
    google_key = os.getenv("GOOGLE_API_KEY")
    for key in ["BASIC_API_KEY", "REASONING_API_KEY", "HIGH_REASONING_API_KEY", "VL_API_KEY"]:
        if not os.getenv(key):
            print(f"[conftest] Setting missing {key} using GOOGLE_API_KEY value.")
            os.environ[key] = google_key

# src ディレクトリへのパスを通す (必要に応じて)
sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))
