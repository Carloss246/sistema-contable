from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    """Configuracion de entorno para Supabase."""

    supabase_url: str
    supabase_key: str
    app_session_secret: str
    anthropic_api_key: str = ""
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.1:8b"



def load_settings() -> Settings:
    load_dotenv()

    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    supabase_key = os.getenv("SUPABASE_KEY", "").strip()
    app_session_secret = os.getenv("APP_SESSION_SECRET", "").strip()
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").strip()
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1:8b").strip()

    if not supabase_url or not supabase_key:
        raise RuntimeError(
            "Faltan variables SUPABASE_URL y/o SUPABASE_KEY en el entorno (.env)."
        )

    if not app_session_secret:
        raise RuntimeError("Falta APP_SESSION_SECRET en el entorno (.env).")

    return Settings(
        supabase_url=supabase_url,
        supabase_key=supabase_key,
        app_session_secret=app_session_secret,
        anthropic_api_key=anthropic_api_key,
        ollama_base_url=ollama_base_url,
        ollama_model=ollama_model,
    )
