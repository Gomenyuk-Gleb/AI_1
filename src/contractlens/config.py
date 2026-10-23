import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    cloud_model: str = os.getenv("CLOUD_MODEL", "gemini/gemini-flash-latest")
    local_model: str = os.getenv("LOCAL_MODEL", "ollama/llama3.2:3b")
    ollama_api_base: str = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
    cost_limit_usd: float = float(os.getenv("COST_LIMIT_USD", "4"))
    request_timeout_s: float = float(os.getenv("REQUEST_TIMEOUT_S", "30"))
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))

    def has_cloud_key(self) -> bool:
        provider = self.cloud_model.split("/")[0]
        key_by_provider = {
            "gemini": "GEMINI_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
        }
        env_name = key_by_provider.get(provider)
        return bool(env_name and os.getenv(env_name))


settings = Settings()
