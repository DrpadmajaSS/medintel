"""
Configuration settings for MedIntel FastAPI backend.
"""

import os
from pydantic import BaseModel, Field


class APISettings(BaseModel):
    """Application configuration and runtime parameters."""
    
    app_name: str = "MedIntel"
    app_version: str = "1.0.0"
    app_subtitle: str = "Medication Intelligence for Proactive Healthcare Operations"
    api_prefix: str = "/api"
    data_dir: str = os.getenv("MEDINTEL_DATA_DIR", "data/raw")
    processed_dir: str = os.getenv("MEDINTEL_PROCESSED_DIR", "data/processed")
    host: str = os.getenv("MEDINTEL_HOST", "0.0.0.0")
    port: int = int(os.getenv("MEDINTEL_PORT", "8000"))
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])


settings = APISettings()
