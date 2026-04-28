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
        """
        Obtiene el Estado de Resultados con la estructura:
        Ventas (70-73) - Descuentos (74) - Costo de Ventas (69) = UTILIDAD BRUTA
        - Gastos Operativos (62+63+64+65+68) = UTILIDAD OPERATIVA
        + Ingresos Financieros (77) + Otros Ingresos (75+76)
        - Gastos Financieros (67) - Otros Gastos (66) = UTILIDAD ANTES DE IMPUESTOS
        - Impuestos (87+88) = UTILIDAD NETA
        """
        saldos = (
            self.client.table("v_saldos_cuentas")
            .select("codigo,nombre,grupo,saldo_neto,saldo_segun_naturaleza")
            .in_("grupo", ["INGRESO", "GASTO"])
            .order("codigo")
            .execute()
            .data
            or []
        )

        # Crear mapa de cuentas para búsqueda rápida
        cuentas_map = {}
        for row in saldos:
            codigo = int(row["codigo"])
            monto = round(float(row["saldo_segun_naturaleza"]), 2)
            cuentas_map[codigo] = {
                "codigo": row["codigo"],
                "nombre": row["nombre"],
                "monto": monto,
            }

        # VENTAS (Cuentas 70-73)
        ventas = sum(float(cuentas_map.get(i, {}).get("monto", 0)) for i in range(70, 74))
        ventas = round(ventas, 2)

        # DESCUENTOS (Cuenta 74)
        # Nota: Cuenta 74 tiene saldo_normal='DEBE', por lo que puede venir negativa
        # Usamos el valor absoluto para restar correctamente
        descuentos_cuenta = cuentas_map.get(74)
        descuentos = round(abs(float(descuentos_cuenta["monto"])), 2) if descuentos_cuenta else 0.0

        # VENTAS NETAS
        ventas_netas = round(ventas - descuentos, 2)

        # COSTO DE VENTAS (Cuenta 69)
        costo_ventas_cuenta = cuentas_map.get(69)
        costo_ventas = round(float(costo_ventas_cuenta["monto"]), 2) if costo_ventas_cuenta else 0.0

        # UTILIDAD BRUTA
        utilidad_bruta = round(ventas_netas - costo_ventas, 2)

        # GASTOS OPERATIVOS (62+63+64+65+68)
        gastos_operativos_cuentas = [cuentas_map.get(i) for i in [62, 63, 64, 65, 68] if i in cuentas_map]
        gastos_operativos = sum(float(c["monto"]) for c in gastos_operativos_cuentas if c)
        gastos_operativos = round(gastos_operativos, 2)

        # UTILIDAD OPERATIVA
        utilidad_operativa = round(utilidad_bruta - gastos_operativos, 2)

        # INGRESOS FINANCIEROS (Cuenta 77)
        ingresos_financieros_cuenta = cuentas_map.get(77)
        ingresos_financieros = round(float(ingresos_financieros_cuenta["monto"]), 2) if ingresos_financieros_cuenta else 0.0

        # GASTOS FINANCIEROS (Cuenta 67)
        gastos_financieros_cuenta = cuentas_map.get(67)
        gastos_financieros = round(float(gastos_financieros_cuenta["monto"]), 2) if gastos_financieros_cuenta else 0.0

        # OTROS INGRESOS (75+76)
        otros_ingresos = sum(float(cuentas_map.get(i, {}).get("monto", 0)) for i in [75, 76])
        otros_ingresos = round(otros_ingresos, 2)

        # OTROS GASTOS (Cuenta 66)
        otros_gastos_cuenta = cuentas_map.get(66)
        otros_gastos = round(float(otros_gastos_cuenta["monto"]), 2) if otros_gastos_cuenta else 0.0

        # UTILIDAD ANTES DE IMPUESTOS
        utilidad_antes_impuestos = round(
            utilidad_operativa + ingresos_financieros + otros_ingresos - gastos_financieros - otros_gastos,
            2
        )

        # IMPUESTOS (87+88)
        impuestos = sum(float(cuentas_map.get(i, {}).get("monto", 0)) for i in [87, 88])
        impuestos = round(impuestos, 2)

        # UTILIDAD NETA
        utilidad_neta = round(utilidad_antes_impuestos - impuestos, 2)

        return {
            "ventas": ventas,
            "descuentos": descuentos,
            "ventas_netas": ventas_netas,
            "costo_ventas": costo_ventas,
            "utilidad_bruta": utilidad_bruta,
            "gastos_operativos": gastos_operativos,
            "utilidad_operativa": utilidad_operativa,
            "ingresos_financieros": ingresos_financieros,
            "gastos_financieros": gastos_financieros,
            "otros_ingresos": otros_ingresos,
            "otros_gastos": otros_gastos,
            "utilidad_antes_impuestos": utilidad_antes_impuestos,
            "impuestos": impuestos,
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

        cuentas_map: dict[int, dict[str, Any]] = {}
        for row in saldos:
            codigo = int(row["codigo"])
            cuentas_map[codigo] = {
                "codigo": row["codigo"],
                "nombre": row["nombre"],
                "monto": round(float(row["saldo_segun_naturaleza"]), 2),
            }

        def monto(codigo: int) -> float:
            return round(float(cuentas_map.get(codigo, {}).get("monto", 0)), 2)

        def suma(codigos: list[int]) -> float:
            return round(sum(monto(codigo) for codigo in codigos), 2)

        # ACTIVO CORRIENTE
        caja_bancos = suma([10, 11])
        cuentas_cobrar = suma([12, 13, 14, 16, 17, 18]) - monto(19)
        inventarios = suma([20, 21, 22, 23, 24, 25, 26, 27, 28]) - monto(29)
        activo_corriente = round(caja_bancos + cuentas_cobrar + inventarios, 2)

        # ACTIVO NO CORRIENTE
        inmuebles_equipos = monto(33)
        intangibles_e_inversiones = suma([30, 31, 32, 34, 35, 37, 38]) - monto(36) - monto(39)
        activo_no_corriente = round(inmuebles_equipos + intangibles_e_inversiones, 2)

        total_activo = round(activo_corriente + activo_no_corriente, 2)

        # PASIVO
        pasivo_corriente = suma([40, 41, 42, 43, 44, 46, 47, 48, 49])
        pasivo_no_corriente = suma([45])
        total_pasivo = round(pasivo_corriente + pasivo_no_corriente, 2)

        # PATRIMONIO
        capital_y_aportes = suma([50, 51, 52, 56])
        reservas = suma([57, 58])
        resultados_acumulados = monto(59)

        utilidad_neta = round(float(self.obtener_estado_resultados()["utilidad_neta"]), 2)

        total_patrimonio = round(capital_y_aportes + reservas + resultados_acumulados + utilidad_neta, 2)
        total_pasivo_mas_patrimonio = round(total_pasivo + total_patrimonio, 2)

        return {
            "activo_corriente": activo_corriente,
            "caja_bancos": caja_bancos,
            "cuentas_cobrar": cuentas_cobrar,
            "inventarios": inventarios,
            "activo_no_corriente": activo_no_corriente,
            "inmuebles_equipos": inmuebles_equipos,
            "intangibles_e_inversiones": intangibles_e_inversiones,
            "total_activo": total_activo,
            "pasivo_corriente": pasivo_corriente,
            "pasivo_no_corriente": pasivo_no_corriente,
            "total_pasivo": total_pasivo,
            "capital_y_aportes": capital_y_aportes,
            "reservas": reservas,
            "resultados_acumulados": resultados_acumulados,
            "utilidad_neta": utilidad_neta,
            "total_patrimonio": total_patrimonio,
            "total_pasivo_mas_patrimonio": total_pasivo_mas_patrimonio,
        }
