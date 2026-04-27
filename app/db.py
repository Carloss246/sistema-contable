from supabase import Client, create_client

from app.config import load_settings



def build_client(access_token: str | None = None) -> Client:
    """Crea y retorna un cliente de Supabase; opcionalmente con token de usuario."""
    settings = load_settings()
    client = create_client(settings.supabase_url, settings.supabase_key)

    # Si hay token de usuario, se aplica al cliente PostgREST para ejecutar
    # consultas con el contexto del usuario autenticado (rol authenticated).
    if access_token:
        client.postgrest.auth(access_token)

    return client
