import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field, HttpUrl


class Settings(BaseSettings):
    """Central configuration for the agent stack."""

    prediction_api_url: HttpUrl = Field(
        "https://ai-health-agent-vuol.onrender.com/predict",
        description="Hosted ML model endpoint returning q10/q50/q90 predictions.",
    )
    ollama_model: str = Field(
        default="phi3",
        description="Ollama model identifier (e.g., 'phi3', 'llama3', 'mistral').",
    )
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Base URL for the local Ollama server.",
    )
    temperature: float = Field(
        default=0.1,
        description="Default temperature for SLM reasoning (keep low for deterministic planning).",
    )
    max_retries: int = Field(default=3, description="HTTP/LLM retry count.")

    class Config:
        env_prefix = "AGENT_"
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Singleton accessor."""
    settings = Settings()
    os.environ.setdefault("OLLAMA_BASE_URL", settings.ollama_base_url)
    return settings

