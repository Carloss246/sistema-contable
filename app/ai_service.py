"""Servicio para procesamiento de asientos contables con IA.

Incluye dos modos:
1. `ollama` (gratis, local)
2. `anthropic` (opcional, con API key)
3. `local-reglas` (gratis, sin API key)
"""

from __future__ import annotations

import json
import re
from datetime import date
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest

try:
    from anthropic import Anthropic
except Exception:  # pragma: no cover - fallback when dependency is unavailable
    Anthropic = None  # type: ignore[assignment]


class AIAsientoService:
    """Procesa descripciones de asientos contables en lenguaje natural."""

    def __init__(
        self,
        api_key: str | None,
        catalogo_cuentas: list[dict[str, Any]],
        ollama_base_url: str = "http://127.0.0.1:11434",
        ollama_model: str = "llama3.1:8b",
    ) -> None:
        self.catalogo = {str(acc["codigo"]): str(acc["nombre"]) for acc in catalogo_cuentas}
        self.catalogo_list = catalogo_cuentas
        self.api_key = (api_key or "").strip()
        self.ollama_base_url = (ollama_base_url or "http://127.0.0.1:11434").rstrip("/")
        self.ollama_model = (ollama_model or "llama3.1:8b").strip()
        self.client = None
        if self.api_key and Anthropic is not None:
            self.client = Anthropic(api_key=self.api_key)

    def parse_asiento(self, texto: str) -> dict[str, Any]:
        """Procesa texto natural y devuelve sugerencia de asiento."""
        if not texto.strip():
            return {
                "error": "El texto no puede estar vacío",
                "fecha": date.today().isoformat(),
                "descripcion": "",
                "movimientos": [],
                "motor": "local-reglas",
            }

        try:
            resultado = self._parse_with_ollama(texto)
            resultado["motor"] = "ollama"
            return self._normalizar_resultado(resultado)
        except Exception:
            pass

        if self.client is not None:
            try:
                resultado = self._parse_with_anthropic(texto)
                resultado["motor"] = "anthropic"
                return self._normalizar_resultado(resultado)
            except Exception:
                # Si falla API externa, pasa automáticamente al modo gratuito local.
                pass

        resultado_local = self._parse_local(texto)
        resultado_local["motor"] = "local-reglas"
        return self._normalizar_resultado(resultado_local)

    def _parse_with_ollama(self, texto: str) -> dict[str, Any]:
        cuentas_disponibles = "\n".join(
            [f"  - {acc['codigo']}: {acc['nombre']}" for acc in self.catalogo_list]
        )
        prompt = f"""Analiza el siguiente texto de una transacción contable y devuelve SOLO JSON válido.

TEXTO:
{texto}

CUENTAS DISPONIBLES:
{cuentas_disponibles}

Salida exacta:
{{
  "fecha": "YYYY-MM-DD",
  "descripcion": "descripcion breve",
  "movimientos": [
    {{"codigo_cuenta": "XX", "descripcion": "detalle", "debe": 0.00, "haber": 0.00}},
    {{"codigo_cuenta": "YY", "descripcion": "detalle", "debe": 0.00, "haber": 0.00}}
  ]
}}

Reglas:
1) Solo códigos existentes en catálogo
2) Cada línea con debe o haber (no ambos)
3) Debe total = Haber total
4) Si no hay fecha, usa {date.today().isoformat()}
5) Devuelve solo JSON, sin markdown
"""

        payload = {
            "model": self.ollama_model,
            "stream": False,
            "format": "json",
            "messages": [{"role": "user", "content": prompt}],
            "options": {"temperature": 0.1},
        }
        data = json.dumps(payload).encode("utf-8")
        req = urlrequest.Request(
            url=f"{self.ollama_base_url}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlrequest.urlopen(req, timeout=15) as resp:
                body = resp.read().decode("utf-8")
        except urlerror.URLError as exc:
            raise RuntimeError(f"No se pudo conectar con Ollama: {exc}") from exc

        parsed = json.loads(body)
        content = str(parsed.get("message", {}).get("content", "")).strip()
        if not content:
            raise RuntimeError("Ollama no devolvió contenido")

        content = re.sub(r"^```json\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
        return json.loads(content)

    def _parse_with_anthropic(self, texto: str) -> dict[str, Any]:
        cuentas_disponibles = "\n".join(
            [f"  - {acc['codigo']}: {acc['nombre']}" for acc in self.catalogo_list]
        )
        prompt = f"""Analiza el siguiente texto de una transacción contable y devuelve SOLO JSON válido.

TEXTO:
{texto}

CUENTAS DISPONIBLES:
{cuentas_disponibles}

Salida exacta:
{{
  "fecha": "YYYY-MM-DD",
  "descripcion": "descripcion breve",
  "movimientos": [
    {{"codigo_cuenta": "XX", "descripcion": "detalle", "debe": 0.00, "haber": 0.00}},
    {{"codigo_cuenta": "YY", "descripcion": "detalle", "debe": 0.00, "haber": 0.00}}
  ]
}}

Reglas:
1) Solo códigos existentes en catálogo
2) Cada línea con debe o haber (no ambos)
3) Debe total = Haber total
4) Si no hay fecha, usa {date.today().isoformat()}
"""
        if self.client is None:
            raise RuntimeError("Cliente Anthropic no inicializado")

        response = self.client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = response.content[0].text.strip()
        response_text = re.sub(r"^```json\s*", "", response_text)
        response_text = re.sub(r"\s*```$", "", response_text)
        return json.loads(response_text)

    def _parse_local(self, texto: str) -> dict[str, Any]:
        text = texto.lower()
        monto = self._extract_amount(texto)
        fecha = self._extract_date(texto)
        descripcion = self._build_description(texto)

        debe_code, haber_code, linea_debe, linea_haber = self._infer_accounts(text)

        movimientos = [
            {
                "codigo_cuenta": debe_code,
                "descripcion": linea_debe,
                "debe": monto,
                "haber": 0.0,
            },
            {
                "codigo_cuenta": haber_code,
                "descripcion": linea_haber,
                "debe": 0.0,
                "haber": monto,
            },
        ]

        warning = ""
        if monto <= 0:
            warning = "No pude detectar monto con certeza. Revísalo antes de guardar."

        return {
            "fecha": fecha,
            "descripcion": descripcion,
            "movimientos": movimientos,
            "warning": warning,
        }

    def _normalizar_resultado(self, resultado: dict[str, Any]) -> dict[str, Any]:
        resultado.setdefault("fecha", date.today().isoformat())
        resultado.setdefault("descripcion", "")
        resultado.setdefault("movimientos", [])

        movimientos_validos: list[dict[str, Any]] = []
        for mov in resultado.get("movimientos", []):
            if not isinstance(mov, dict):
                continue
            codigo = str(mov.get("codigo_cuenta", "")).strip()
            if not codigo:
                continue
            debe = float(mov.get("debe", 0) or 0)
            haber = float(mov.get("haber", 0) or 0)
            movimientos_validos.append(
                {
                    "codigo_cuenta": codigo,
                    "descripcion": str(mov.get("descripcion", "")),
                    "debe": round(debe, 2),
                    "haber": round(haber, 2),
                }
            )

        resultado["movimientos"] = movimientos_validos
        return resultado

    def _extract_amount(self, texto: str) -> float:
        money_like = re.findall(
            r"(?:\$|s/|usd|quetzales|q\.?|bs\.?|euros?)\s*([0-9][0-9.,]*)",
            texto,
            flags=re.IGNORECASE,
        )
        if money_like:
            return self._to_float(money_like[0])

        texto_sin_fecha = re.sub(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", " ", texto)
        nums = re.findall(r"\b\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?\b", texto_sin_fecha)
        candidates = [self._to_float(n) for n in nums]
        candidates = [n for n in candidates if n > 0]
        return round(max(candidates), 2) if candidates else 0.0

    def _extract_date(self, texto: str) -> str:
        iso = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", texto)
        if iso:
            return iso.group(0)

        dmy = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b", texto)
        if dmy:
            d = int(dmy.group(1))
            m = int(dmy.group(2))
            y = int(dmy.group(3))
            if y < 100:
                y += 2000
            try:
                return date(y, m, d).isoformat()
            except ValueError:
                pass

        return date.today().isoformat()

    def _build_description(self, texto: str) -> str:
        first_line = texto.strip().split("\n", maxsplit=1)[0].strip()
        if len(first_line) > 120:
            return first_line[:120].rstrip() + "..."
        return first_line or "Asiento generado por asistente"

    def _infer_accounts(self, text: str) -> tuple[str, str, str, str]:
        efectivo = self._find_code(["efectivo", "caja"])
        bancos = self._find_code(["banco", "bancos"])
        ventas = self._find_code(["venta", "ventas", "ingreso", "ingresos"])
        compras = self._find_code(["compra", "compras", "mercader", "inventario"])
        capital = self._find_code(["capital", "aporte"])
        cxp = self._find_code(["pagar", "proveedor"])  # cuentas por pagar
        cxc = self._find_code(["cobrar", "cliente"])  # cuentas por cobrar
        gasto = self._find_code(["gasto", "servicio", "alquiler", "sueldo", "impuesto"])

        caja_o_banco = bancos or efectivo

        if any(k in text for k in ["aporte", "capital inicial", "inversion del propietario"]):
            return (
                caja_o_banco,
                capital,
                "Ingreso de fondos",
                "Registro de capital",
            )

        if any(k in text for k in ["deposit", "deposito"]):
            return (
                bancos,
                efectivo,
                "Depósito en banco",
                "Salida de caja",
            )

        if any(k in text for k in ["retiro", "retiramos", "extraccion"]):
            return (
                efectivo,
                bancos,
                "Ingreso de efectivo",
                "Salida de banco",
            )

        if any(k in text for k in ["venta", "vendimos", "facturamos"]):
            if any(k in text for k in ["credito", "a credito"]):
                return (
                    cxc,
                    ventas,
                    "Venta al crédito",
                    "Ingreso por ventas",
                )
            return (
                caja_o_banco,
                ventas,
                "Cobro de venta",
                "Ingreso por ventas",
            )

        if any(k in text for k in ["compra", "compramos", "adquirimos"]):
            if any(k in text for k in ["credito", "a credito"]):
                return (
                    compras,
                    cxp,
                    "Compra al crédito",
                    "Cuenta por pagar",
                )
            return (
                compras,
                caja_o_banco,
                "Compra de bienes/mercadería",
                "Pago de compra",
            )

        if any(k in text for k in ["pago", "pagamos", "cancelamos", "gasto", "servicio"]):
            return (
                gasto,
                caja_o_banco,
                "Registro de gasto",
                "Pago en efectivo/banco",
            )

        return (
            compras,
            caja_o_banco,
            "Registro de operación",
            "Contrapartida",
        )

    def _find_code(self, keywords: list[str]) -> str:
        for codigo, nombre in self.catalogo.items():
            lower_name = nombre.lower()
            if any(k in lower_name for k in keywords):
                return codigo
        # Fallback seguro al primer código disponible del catálogo
        return next(iter(self.catalogo.keys()), "10")

    @staticmethod
    def _to_float(raw: str) -> float:
        value = raw.strip().replace(" ", "")
        if "," in value and "." in value:
            # 1,234.56 -> 1234.56
            if value.rfind(".") > value.rfind(","):
                value = value.replace(",", "")
            else:
                # 1.234,56 -> 1234.56
                value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", ".")
        try:
            return round(float(value), 2)
        except ValueError:
            return 0.0
