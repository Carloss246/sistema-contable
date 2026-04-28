from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.accounting_service import AccountingService, MovimientoInput
from app.config import load_settings
from app.db import build_client


BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Sistema Contable")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

settings = load_settings()
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.app_session_secret,
    same_site="lax",
    https_only=False,
)



def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)



def _build_movimientos_from_form(form: Any) -> list[MovimientoInput]:
    codigos = form.getlist("codigo_cuenta")
    descripciones = form.getlist("descripcion_linea")
    debes = form.getlist("debe")
    haberes = form.getlist("haber")

    movimientos: list[MovimientoInput] = []
    for i, codigo in enumerate(codigos):
        codigo = codigo.strip()
        if not codigo:
            continue

        descripcion = (descripciones[i] if i < len(descripciones) else "").strip()
        debe = float((debes[i] if i < len(debes) else "0") or 0)
        haber = float((haberes[i] if i < len(haberes) else "0") or 0)

        if debe == 0 and haber == 0:
            continue

        movimientos.append(
            MovimientoInput(
                codigo_cuenta=codigo,
                descripcion=descripcion,
                debe=debe,
                haber=haber,
            )
        )

    return movimientos



def _dashboard_data(service: AccountingService) -> dict[str, Any]:
    catalogo = service.obtener_catalogo()
    diario = service.obtener_libro_diario()
    estado_resultados = service.obtener_estado_resultados()
    return {
        "cuentas": len(catalogo),
        "movimientos": len(diario),
        "asientos": len({row["numero_asiento"] for row in diario}),
        "saldo_total": round(float(estado_resultados["utilidad_neta"]), 2),
    }


def _is_authenticated(request: Request) -> bool:
    return bool(request.session.get("access_token"))


def _store_auth_session(request: Request, auth_response: Any) -> bool:
    session_data = getattr(auth_response, "session", None)
    user_data = getattr(auth_response, "user", None)
    if not session_data:
        return False

    request.session["access_token"] = session_data.access_token
    request.session["refresh_token"] = session_data.refresh_token

    # Si user no llega en el refresh, conservamos el correo actual.
    if user_data:
        request.session["user_email"] = user_data.email
        request.session["user_id"] = user_data.id

    return True


def _ensure_valid_session(request: Request) -> bool:
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")
    if not access_token:
        return False

    auth_client = build_client()
    try:
        # set_session valida token actual y permite recuperar una sesión consistente.
        auth_response = auth_client.auth.set_session(access_token, refresh_token)
        _store_auth_session(request, auth_response)
        return True
    except Exception:
        if not refresh_token:
            request.session.clear()
            return False

    try:
        # Si el access token expiro, intentamos renovarlo con refresh token.
        refresh_response = auth_client.auth.refresh_session(refresh_token)
        if _store_auth_session(request, refresh_response):
            return True
    except Exception:
        pass

    request.session.clear()
    return False


def _protected_redirect(request: Request) -> RedirectResponse | None:
    if not _is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)
    if not _ensure_valid_session(request):
        return RedirectResponse(url="/login", status_code=303)
    return None


def _template_context(request: Request, title: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    context: dict[str, Any] = {
        "request": request,
        "title": title,
        "authenticated": _is_authenticated(request),
        "current_user": request.session.get("user_email"),
    }
    if extra:
        context.update(extra)
    return context


def _service_for_request(request: Request) -> AccountingService:
    access_token = request.session.get("access_token")
    if not access_token:
        raise RuntimeError("No existe sesión activa")
    return AccountingService(build_client(access_token=access_token))


def _render_error(request: Request, message: str, detail: str | None = None, status_code: int = 500):
    return templates.TemplateResponse(
        request,
        "error.html",
        _template_context(
            request,
            "Error del sistema",
            {
                "message": message,
                "detail": detail,
            },
        ),
        status_code=status_code,
    )


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str | None = None):
    if _is_authenticated(request):
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        request,
        "login.html",
        _template_context(request, "Iniciar sesion", {"error": error}),
    )


@app.post("/login")
async def login_submit(request: Request):
    form = await request.form()
    email = str(form.get("email", "")).strip().lower()
    password = str(form.get("password", "")).strip()

    if not email or not password:
        return templates.TemplateResponse(
            request,
            "login.html",
            _template_context(
                request,
                "Iniciar sesion",
                {"error": "Debes indicar correo y contraseña"},
            ),
            status_code=400,
        )

    auth_client = build_client()
    try:
        auth_response = auth_client.auth.sign_in_with_password(
            {"email": email, "password": password}
        )
    except Exception as exc:
        return templates.TemplateResponse(
            request,
            "login.html",
            _template_context(
                request,
                "Iniciar sesion",
                {"error": f"No fue posible iniciar sesion: {exc}"},
            ),
            status_code=401,
        )

    session_data = getattr(auth_response, "session", None)
    user_data = getattr(auth_response, "user", None)

    if not session_data or not user_data:
        return templates.TemplateResponse(
            request,
            "login.html",
            _template_context(
                request,
                "Iniciar sesion",
                {
                    "error": "No se obtuvo una sesion valida. Revisa confirmacion de correo en Supabase Auth.",
                },
            ),
            status_code=401,
        )

    _store_auth_session(request, auth_response)

    return RedirectResponse(url="/", status_code=303)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return _render_error(
        request,
        "Ocurrió un error al cargar la página.",
        detail=str(exc),
        status_code=500,
    )


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    auth_redirect = _protected_redirect(request)
    if auth_redirect:
        return auth_redirect

    try:
        service = _service_for_request(request)
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            _template_context(request, "Panel principal", {"stats": _dashboard_data(service)}),
        )
    except Exception as exc:
        return _render_error(
            request,
            "No se pudo cargar el panel principal.",
            detail=str(exc),
        )


@app.get("/catalogo", response_class=HTMLResponse)
def catalogo(request: Request):
    auth_redirect = _protected_redirect(request)
    if auth_redirect:
        return auth_redirect

    try:
        service = _service_for_request(request)
        rows = service.obtener_catalogo()
        return templates.TemplateResponse(
            request,
            "table_page.html",
            _template_context(
                request,
                "Catalogo de cuentas",
                {
                    "heading": "Catalogo de cuentas",
                    "rows": rows,
                    "columns": ["codigo", "nombre", "grupo", "saldo_normal", "activa"],
                },
            ),
        )
    except Exception as exc:
        return _render_error(request, "No se pudo cargar el catalogo.", str(exc))


@app.get("/asientos/nuevo", response_class=HTMLResponse)
def nuevo_asiento(request: Request, error: str | None = None):
    auth_redirect = _protected_redirect(request)
    if auth_redirect:
        return auth_redirect

    try:
        service = _service_for_request(request)
        return templates.TemplateResponse(
            request,
            "asiento_form.html",
            _template_context(
                request,
                "Nuevo asiento",
                {
                    "catalogo": service.obtener_catalogo(),
                    "error": error,
                    "hoy": date.today().isoformat(),
                },
            ),
        )
    except Exception as exc:
        return _render_error(request, "No se pudo abrir el formulario de asiento.", str(exc))


@app.post("/asientos")
async def crear_asiento(request: Request):
    auth_redirect = _protected_redirect(request)
    if auth_redirect:
        return auth_redirect

    service = _service_for_request(request)

    form = await request.form()
    fecha = _parse_date(form.get("fecha")) or date.today()
    descripcion = str(form.get("descripcion", "")).strip()
    fuente = str(form.get("fuente", "MANUAL")).strip() or "MANUAL"
    creado_por = str(form.get("creado_por", "USUARIO")).strip() or "USUARIO"

    movimientos = _build_movimientos_from_form(form)

    try:
        if not descripcion:
            raise ValueError("La descripcion del asiento es obligatoria")
        asiento_id = service.registrar_asiento(
            fecha=fecha,
            descripcion=descripcion,
            movimientos=movimientos,
            fuente=fuente,
            creado_por=creado_por,
        )
        return RedirectResponse(url=f"/asientos/{asiento_id}", status_code=303)
    except Exception as exc:
        return templates.TemplateResponse(
            request,
            "asiento_form.html",
            _template_context(
                request,
                "Nuevo asiento",
                {
                    "catalogo": service.obtener_catalogo(),
                    "error": str(exc),
                    "hoy": fecha.isoformat(),
                },
            ),
            status_code=400,
        )


@app.get("/asientos/{asiento_id}", response_class=HTMLResponse)
def asiento_exitoso(request: Request, asiento_id: str):
    auth_redirect = _protected_redirect(request)
    if auth_redirect:
        return auth_redirect

    try:
        return templates.TemplateResponse(
            request,
            "success.html",
            _template_context(
                request,
                "Asiento guardado",
                {
                    "message": f"Asiento registrado con id {asiento_id}",
                    "back_url": "/asientos/nuevo",
                },
            ),
        )
    except Exception as exc:
        return _render_error(request, "No se pudo mostrar la confirmacion.", str(exc))


@app.get("/diario", response_class=HTMLResponse)
def diario(request: Request, desde: str | None = None, hasta: str | None = None):
    auth_redirect = _protected_redirect(request)
    if auth_redirect:
        return auth_redirect

    try:
        service = _service_for_request(request)
        rows = service.obtener_libro_diario(_parse_date(desde), _parse_date(hasta))
        return templates.TemplateResponse(
            request,
            "report_page.html",
            _template_context(
                request,
                "Libro diario",
                {
                    "heading": "Libro diario",
                    "rows": rows,
                    "columns": ["numero_asiento", "fecha", "descripcion_asiento", "codigo_cuenta", "nombre_cuenta", "debe", "haber"],
                },
            ),
        )
    except Exception as exc:
        return _render_error(request, "No se pudo cargar el libro diario.", str(exc))


@app.get("/mayor", response_class=HTMLResponse)
def mayor(request: Request, cuenta: str | None = None, desde: str | None = None, hasta: str | None = None):
    auth_redirect = _protected_redirect(request)
    if auth_redirect:
        return auth_redirect

    try:
        service = _service_for_request(request)
        rows = service.obtener_mayor(cuenta, _parse_date(desde), _parse_date(hasta))
        
        # Agrupar movimientos por cuenta manualmente
        cuentas_dict = {}
        for row in rows:
            cod = row.get("codigo_cuenta")
            if not cod:
                continue
            if cod not in cuentas_dict:
                cuentas_dict[cod] = {
                    "codigo": cod,
                    "nombre": row.get("nombre_cuenta", ""),
                    "debe_rows": [],
                    "haber_rows": [],
                    "total_debe": 0.0,
                    "total_haber": 0.0,
                }
            
            # Separar por debe/haber
            debe = float(row.get("debe") or 0)
            haber = float(row.get("haber") or 0)
            
            if debe > 0:
                cuentas_dict[cod]["debe_rows"].append({
                    "fecha": row.get("fecha"),
                    "desc": row.get("descripcion_asiento"),
                    "asiento": row.get("numero_asiento"),
                    "monto": debe
                })
                cuentas_dict[cod]["total_debe"] += debe
            
            if haber > 0:
                cuentas_dict[cod]["haber_rows"].append({
                    "fecha": row.get("fecha"),
                    "desc": row.get("descripcion_asiento"),
                    "asiento": row.get("numero_asiento"),
                    "monto": haber
                })
                cuentas_dict[cod]["total_haber"] += haber
        
        cuentas_list = sorted(cuentas_dict.values(), key=lambda x: x["codigo"])
        
        context = _template_context(
            request,
            "Libro mayor",
            {
                "heading": "Libro mayor",
                "cuentas": cuentas_list,
            },
        )
        
        return templates.TemplateResponse(
            request,
            "mayor.html",
            context,
        )
    except Exception as exc:
        return _render_error(request, "No se pudo cargar el libro mayor.", str(exc))


@app.get("/balanza", response_class=HTMLResponse)
def balanza(request: Request):
    auth_redirect = _protected_redirect(request)
    if auth_redirect:
        return auth_redirect

    try:
        service = _service_for_request(request)
        rows = service.obtener_balanza()
        
        # Filtrar solo cuentas con movimientos (donde hay saldo)
        rows = [row for row in rows if (
            float(row.get("total_debe") or 0) > 0 or 
            float(row.get("total_haber") or 0) > 0
        )]
        
        # Calcular totales
        total_debe = sum(float(row.get("total_debe") or 0) for row in rows)
        total_haber = sum(float(row.get("total_haber") or 0) for row in rows)
        
        return templates.TemplateResponse(
            request,
            "balanza_page.html",
            _template_context(
                request,
                "Balanza de comprobacion",
                {
                    "heading": "Balanza de comprobacion",
                    "rows": rows,
                    "columns": ["codigo", "nombre", "grupo", "total_debe", "total_haber", "saldo_deudor", "saldo_acreedor"],
                    "total_debe": total_debe,
                    "total_haber": total_haber,
                },
            ),
        )
    except Exception as exc:
        return _render_error(request, "No se pudo cargar la balanza.", str(exc))


@app.get("/estado-resultados", response_class=HTMLResponse)
def estado_resultados(request: Request):
    auth_redirect = _protected_redirect(request)
    if auth_redirect:
        return auth_redirect

    try:
        service = _service_for_request(request)
        data = service.obtener_estado_resultados()
        return templates.TemplateResponse(
            request,
            "estado_resultados.html",
            _template_context(request, "Estado de resultados", {"data": data}),
        )
    except Exception as exc:
        return _render_error(request, "No se pudo cargar el estado de resultados.", str(exc))


@app.get("/balance-general", response_class=HTMLResponse)
def balance_general(request: Request):
    auth_redirect = _protected_redirect(request)
    if auth_redirect:
        return auth_redirect

    try:
        service = _service_for_request(request)
        data = service.obtener_balance_general()
        return templates.TemplateResponse(
            request,
            "balance_general.html",
            _template_context(request, "Balance general", {"data": data}),
        )
    except Exception as exc:
        return _render_error(request, "No se pudo cargar el balance general.", str(exc))


@app.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request, error: str | None = None, message: str | None = None):
    if _is_authenticated(request):
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        request,
        "signup.html",
        _template_context(
            request,
            "Registro",
            {
                "error": error,
                "message": message,
            },
        ),
    )


@app.post("/signup")
async def signup_submit(request: Request):
    form = await request.form()
    email = str(form.get("email", "")).strip().lower()
    password = str(form.get("password", "")).strip()

    if not email or not password:
        return templates.TemplateResponse(
            request,
            "signup.html",
            _template_context(
                request,
                "Registro",
                {"error": "Debes indicar correo y contraseña"},
            ),
            status_code=400,
        )

    auth_client = build_client()
    try:
        auth_response = auth_client.auth.sign_up({"email": email, "password": password})
    except Exception as exc:
        return templates.TemplateResponse(
            request,
            "signup.html",
            _template_context(
                request,
                "Registro",
                {"error": f"No fue posible registrar el usuario: {exc}"},
            ),
            status_code=400,
        )

    session_data = getattr(auth_response, "session", None)
    user_data = getattr(auth_response, "user", None)

    if session_data and user_data:
        _store_auth_session(request, auth_response)
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        request,
        "signup.html",
        _template_context(
            request,
            "Registro",
            {
                "message": "Usuario creado. Revisa tu correo para confirmar la cuenta y luego inicia sesion.",
            },
        ),
        status_code=200,
    )
