from dataclasses import dataclass
import os
import logging

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    """Configuracion de entorno para Supabase."""

    supabase_url: str
    supabase_key: str
    app_session_secret: str
    # IA settings removed



def load_settings() -> Settings:
    load_dotenv()

    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    supabase_key = os.getenv("SUPABASE_KEY", "").strip()
    app_session_secret = os.getenv("APP_SESSION_SECRET", "").strip()
    # IA env vars removed

    if not supabase_url or not supabase_key:
        raise RuntimeError(
            "Faltan variables SUPABASE_URL y/o SUPABASE_KEY en el entorno (.env)."
        )

    if not app_session_secret:
        import secrets
        generated = secrets.token_hex(32)
        logging.getLogger(__name__).warning(
            "APP_SESSION_SECRET no encontrada en el entorno; se generó una secret temporal. "
            "Define APP_SESSION_SECRET en Vercel/entorno para producción."
        )
        app_session_secret = generated

    return Settings(
        supabase_url=supabase_url,
        supabase_key=supabase_key,
        app_session_secret=app_session_secret,
    )
