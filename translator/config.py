# config.py
from dataclasses import dataclass
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass
class LLMConfig:
    """Configuration for the LLM service"""
    base_url: str = os.getenv("BASE_URL", "http://localhost:11434/v1")
    api_key: str = os.getenv("OPENAI_API_KEY", "None")
    model: str = os.getenv("LLM_MODEL", "qwen2.5:72b")
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0"))
    max_tokens: Optional[int] = int(os.getenv("LLM_MAX_TOKENS", "0")) or None
    top_p: float = float(os.getenv("LLM_TOP_P", "1.0"))
    frequency_penalty: float = float(os.getenv("LLM_FREQUENCY_PENALTY", "0"))
    presence_penalty: float = float(os.getenv("LLM_PRESENCE_PENALTY", "0"))


@dataclass
class TranslationConfig:
    """Configuration class for translation parameters"""

    target_language: str = "German"
    source_language: Optional[str] = None
    domain: Optional[str] = None
    tone: Optional[str] = None
    glossary: Optional[str] = None
    context: Optional[str] = None