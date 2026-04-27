from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from supabase import Client


@dataclass
class MovimientoInput:
    codigo_cuenta: str
    descripcion: str
    debe: float = 0.0
    haber: float = 0.0


class AccountingService:
    """Servicios contables sobre Supabase siguiendo partida doble."""

    def __init__(self, client: Client) -> None:
        self.client = client

    def registrar_asiento(
        self,
        fecha: date,
        descripcion: str,
        movimientos: list[MovimientoInput],
        fuente: str = "MANUAL",
        creado_por: str = "USUARIO",
    ) -> str:
        if len(movimientos) < 2:
            raise ValueError("Un asiento necesita al menos 2 movimientos")

        payload_movimientos: list[dict[str, Any]] = [
            {
                "codigo_cuenta": m.codigo_cuenta,
                "descripcion": m.descripcion,
                "debe": round(float(m.debe), 2),
                "haber": round(float(m.haber), 2),
            }
            for m in movimientos
        ]

        total_debe = round(sum(m["debe"] for m in payload_movimientos), 2)
        total_haber = round(sum(m["haber"] for m in payload_movimientos), 2)
        if total_debe != total_haber:
            raise ValueError(
                f"Partida doble no cumple (debe={total_debe}, haber={total_haber})"
            )

        result = self.client.rpc(
            "fn_registrar_asiento",
            {
                "p_fecha": fecha.isoformat(),
                "p_descripcion": descripcion,
                "p_fuente": fuente,
                "p_creado_por": creado_por,
                "p_movimientos": payload_movimientos,
            },
        ).execute()

        if result.data is None:
            raise RuntimeError("No se recibio id de asiento desde Supabase")

        return str(result.data)

    def obtener_catalogo(self) -> list[dict[str, Any]]:
        result = (
            self.client.table("catalogo_cuentas")
            .select("codigo,nombre,grupo,saldo_normal,activa")
            .order("codigo")
            .execute()
        )
        return result.data or []

    def obtener_libro_diario(
        self, desde: date | None = None, hasta: date | None = None
    ) -> list[dict[str, Any]]:
        query = self.client.table("v_libro_diario").select("*")

        if desde:
            query = query.gte("fecha", desde.isoformat())
        if hasta:
            query = query.lte("fecha", hasta.isoformat())

        result = query.order("fecha").order("numero_asiento").order("linea").execute()
        return result.data or []

    def obtener_mayor(
        self,
        codigo_cuenta: str | None = None,
        desde: date | None = None,
        hasta: date | None = None,
    ) -> list[dict[str, Any]]:
        query = self.client.table("v_mayor").select("*")

        if codigo_cuenta:
            query = query.eq("codigo_cuenta", codigo_cuenta)
        if desde:
            query = query.gte("fecha", desde.isoformat())
        if hasta:
            query = query.lte("fecha", hasta.isoformat())

        result = query.order("codigo_cuenta").order("fecha").order("numero_asiento").execute()
        return result.data or []

    def obtener_balanza(self) -> list[dict[str, Any]]:
        result = (
            self.client.table("v_balanza_comprobacion")
            .select("*")
            .order("codigo")
            .execute()
        )
        return result.data or []

    def obtener_estado_resultados(self) -> dict[str, Any]:
        saldos = (
            self.client.table("v_saldos_cuentas")
            .select("codigo,nombre,grupo,saldo_neto,saldo_segun_naturaleza")
            .in_("grupo", ["INGRESO", "GASTO"])
            .order("codigo")
            .execute()
            .data
            or []
        )

        ingresos: list[dict[str, Any]] = []
        gastos: list[dict[str, Any]] = []

        total_ingresos = 0.0
        total_gastos = 0.0

        for row in saldos:
            monto = round(float(row["saldo_segun_naturaleza"]), 2)
            item = {
                "codigo": row["codigo"],
                "nombre": row["nombre"],
                "monto": monto,
            }
            if row["grupo"] == "INGRESO":
                ingresos.append(item)
                total_ingresos += monto
            else:
                gastos.append(item)
                total_gastos += monto

        utilidad_neta = round(total_ingresos - total_gastos, 2)

        return {
            "ingresos": ingresos,
            "gastos": gastos,
            "total_ingresos": round(total_ingresos, 2),
            "total_gastos": round(total_gastos, 2),
            "utilidad_neta": utilidad_neta,
        }

    def obtener_balance_general(self) -> dict[str, Any]:
        saldos = (
            self.client.table("v_saldos_cuentas")
            .select("codigo,nombre,grupo,saldo_segun_naturaleza")
            .in_("grupo", ["ACTIVO", "PASIVO", "CAPITAL", "INGRESO", "GASTO"])
            .order("codigo")
            .execute()
            .data
            or []
        )

        activos: list[dict[str, Any]] = []
        pasivos: list[dict[str, Any]] = []
        capital: list[dict[str, Any]] = []

        total_activos = 0.0
        total_pasivos = 0.0
        total_capital = 0.0
        total_ingresos = 0.0
        total_gastos = 0.0

        for row in saldos:
            monto = round(float(row["saldo_segun_naturaleza"]), 2)
            grupo = row["grupo"]
            item = {"codigo": row["codigo"], "nombre": row["nombre"], "monto": monto}

            if grupo == "ACTIVO":
                activos.append(item)
                total_activos += monto
            elif grupo == "PASIVO":
                pasivos.append(item)
                total_pasivos += monto
            elif grupo == "CAPITAL":
                capital.append(item)
                total_capital += monto
            elif grupo == "INGRESO":
                total_ingresos += monto
            elif grupo == "GASTO":
                total_gastos += monto

        utilidad_neta = round(total_ingresos - total_gastos, 2)

        # Se incorpora la utilidad neta al capital para el equilibrio del balance.
        capital.append({"codigo": "ER", "nombre": "Utilidad del ejercicio", "monto": utilidad_neta})
        total_capital_ajustado = round(total_capital + utilidad_neta, 2)

        return {
            "activos": activos,
            "pasivos": pasivos,
            "capital": capital,
            "total_activos": round(total_activos, 2),
            "total_pasivos": round(total_pasivos, 2),
            "total_capital": total_capital_ajustado,
            "pasivo_mas_capital": round(total_pasivos + total_capital_ajustado, 2),
        }
