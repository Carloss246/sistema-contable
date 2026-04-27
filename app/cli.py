from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path

from app.accounting_service import AccountingService, MovimientoInput
from app.db import build_client
from app.report_printer import (
    imprimir_balance_general,
    imprimir_balanza,
    imprimir_catalogo,
    imprimir_diario,
    imprimir_estado_resultados,
    imprimir_mayor,
)



def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)



def _load_movimientos(path: str) -> list[MovimientoInput]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    movimientos: list[MovimientoInput] = []

    for item in payload:
        movimientos.append(
            MovimientoInput(
                codigo_cuenta=item["codigo_cuenta"],
                descripcion=item.get("descripcion", ""),
                debe=float(item.get("debe", 0)),
                haber=float(item.get("haber", 0)),
            )
        )

    return movimientos



def main() -> None:
    parser = argparse.ArgumentParser(description="Sistema contable con Python + Supabase")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("catalogo", help="Muestra catalogo de cuentas")

    p_registrar = sub.add_parser("registrar-asiento", help="Registra un asiento")
    p_registrar.add_argument("--fecha", required=True, help="Fecha YYYY-MM-DD")
    p_registrar.add_argument("--descripcion", required=True, help="Descripcion del asiento")
    p_registrar.add_argument("--archivo", required=True, help="JSON de movimientos")
    p_registrar.add_argument("--fuente", default="MANUAL")
    p_registrar.add_argument("--creado-por", default="USUARIO")

    p_diario = sub.add_parser("diario", help="Muestra libro diario")
    p_diario.add_argument("--desde", help="Fecha inicio YYYY-MM-DD")
    p_diario.add_argument("--hasta", help="Fecha fin YYYY-MM-DD")

    p_mayor = sub.add_parser("mayor", help="Muestra libro mayor")
    p_mayor.add_argument("--cuenta", help="Codigo de cuenta (ej. 101)")
    p_mayor.add_argument("--desde", help="Fecha inicio YYYY-MM-DD")
    p_mayor.add_argument("--hasta", help="Fecha fin YYYY-MM-DD")

    sub.add_parser("balanza", help="Muestra balanza de comprobacion")
    sub.add_parser("estado-resultados", help="Muestra estado de resultados")
    sub.add_parser("balance-general", help="Muestra balance general")

    args = parser.parse_args()

    service = AccountingService(build_client())

    if args.cmd == "catalogo":
        imprimir_catalogo(service.obtener_catalogo())
        return

    if args.cmd == "registrar-asiento":
        movimientos = _load_movimientos(args.archivo)
        asiento_id = service.registrar_asiento(
            fecha=_parse_date(args.fecha) or date.today(),
            descripcion=args.descripcion,
            movimientos=movimientos,
            fuente=args.fuente,
            creado_por=args.creado_por,
        )
        print(f"Asiento registrado con id: {asiento_id}")
        return

    if args.cmd == "diario":
        rows = service.obtener_libro_diario(_parse_date(args.desde), _parse_date(args.hasta))
        imprimir_diario(rows)
        return

    if args.cmd == "mayor":
        rows = service.obtener_mayor(args.cuenta, _parse_date(args.desde), _parse_date(args.hasta))
        imprimir_mayor(rows)
        return

    if args.cmd == "balanza":
        imprimir_balanza(service.obtener_balanza())
        return

    if args.cmd == "estado-resultados":
        imprimir_estado_resultados(service.obtener_estado_resultados())
        return

    if args.cmd == "balance-general":
        imprimir_balance_general(service.obtener_balance_general())


if __name__ == "__main__":
    main()
