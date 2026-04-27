from __future__ import annotations

from collections import defaultdict
from typing import Any



def _money(value: float) -> str:
    return f"{value:,.2f}"



def imprimir_catalogo(rows: list[dict[str, Any]]) -> None:
    print("\nCATALOGO DE CUENTAS")
    print("-" * 72)
    print(f"{'CODIGO':<10}{'NOMBRE':<35}{'GRUPO':<12}{'SALDO':<10}")
    print("-" * 72)
    for r in rows:
        print(f"{r['codigo']:<10}{r['nombre']:<35}{r['grupo']:<12}{r['saldo_normal']:<10}")



def imprimir_diario(rows: list[dict[str, Any]]) -> None:
    print("\nLIBRO DIARIO")
    print("=" * 96)
    if not rows:
        print("Sin movimientos")
        return

    current = None
    for r in rows:
        asiento = (r["numero_asiento"], r["fecha"], r["descripcion_asiento"])
        if asiento != current:
            current = asiento
            print("-" * 96)
            print(f"Asiento #{r['numero_asiento']} | Fecha: {r['fecha']} | {r['descripcion_asiento']}")
            print("-" * 96)
            print(f"{'Cuenta':<10}{'Nombre':<38}{'Debe':>18}{'Haber':>18}")

        print(
            f"{r['codigo_cuenta']:<10}{r['nombre_cuenta']:<38}"
            f"{_money(float(r['debe'])):>18}{_money(float(r['haber'])):>18}"
        )



def imprimir_mayor(rows: list[dict[str, Any]]) -> None:
    print("\nLIBRO MAYOR")
    print("=" * 110)
    if not rows:
        print("Sin movimientos")
        return

    grupos = defaultdict(list)
    for r in rows:
        grupos[(r["codigo_cuenta"], r["nombre_cuenta"])].append(r)

    for (codigo, nombre), items in grupos.items():
        print("-" * 110)
        print(f"Cuenta {codigo} - {nombre}")
        print("-" * 110)
        print(f"{'Fecha':<12}{'Asiento':<10}{'Descripcion':<52}{'Debe':>16}{'Haber':>16}")

        saldo = 0.0
        for m in items:
            debe = float(m["debe"])
            haber = float(m["haber"])
            saldo += debe - haber
            print(
                f"{m['fecha']:<12}{m['numero_asiento']:<10}{(m['descripcion_asiento'] or '')[:50]:<52}"
                f"{_money(debe):>16}{_money(haber):>16}"
            )

        print(f"Saldo neto cuenta {codigo}: {_money(saldo)}")



def imprimir_balanza(rows: list[dict[str, Any]]) -> None:
    print("\nBALANZA DE COMPROBACION")
    print("=" * 110)
    if not rows:
        print("Sin saldos")
        return

    print(f"{'Codigo':<10}{'Cuenta':<34}{'Debe':>16}{'Haber':>16}{'Saldo Deudor':>16}{'Saldo Acreedor':>16}")
    print("-" * 110)

    total_debe = 0.0
    total_haber = 0.0
    total_deudor = 0.0
    total_acreedor = 0.0

    for r in rows:
        debe = float(r["total_debe"])
        haber = float(r["total_haber"])
        deudor = float(r["saldo_deudor"])
        acreedor = float(r["saldo_acreedor"])

        total_debe += debe
        total_haber += haber
        total_deudor += deudor
        total_acreedor += acreedor

        print(
            f"{r['codigo']:<10}{r['nombre'][:32]:<34}"
            f"{_money(debe):>16}{_money(haber):>16}{_money(deudor):>16}{_money(acreedor):>16}"
        )

    print("-" * 110)
    print(
        f"{'TOTALES':<44}{_money(total_debe):>16}{_money(total_haber):>16}"
        f"{_money(total_deudor):>16}{_money(total_acreedor):>16}"
    )



def imprimir_estado_resultados(data: dict[str, Any]) -> None:
    print("\nESTADO DE RESULTADOS")
    print("=" * 72)

    print("Ingresos")
    print("-" * 72)
    for item in data["ingresos"]:
        print(f"{item['codigo']:<10}{item['nombre']:<44}{_money(float(item['monto'])):>18}")

    print("-" * 72)
    print(f"{'Total ingresos':<54}{_money(float(data['total_ingresos'])):>18}")

    print("\nGastos")
    print("-" * 72)
    for item in data["gastos"]:
        print(f"{item['codigo']:<10}{item['nombre']:<44}{_money(float(item['monto'])):>18}")

    print("-" * 72)
    print(f"{'Total gastos':<54}{_money(float(data['total_gastos'])):>18}")
    print("=" * 72)
    print(f"{'Utilidad neta':<54}{_money(float(data['utilidad_neta'])):>18}")



def imprimir_balance_general(data: dict[str, Any]) -> None:
    print("\nBALANCE GENERAL")
    print("=" * 72)

    print("Activos")
    print("-" * 72)
    for item in data["activos"]:
        print(f"{item['codigo']:<10}{item['nombre']:<44}{_money(float(item['monto'])):>18}")
    print("-" * 72)
    print(f"{'Total activos':<54}{_money(float(data['total_activos'])):>18}")

    print("\nPasivos")
    print("-" * 72)
    for item in data["pasivos"]:
        print(f"{item['codigo']:<10}{item['nombre']:<44}{_money(float(item['monto'])):>18}")
    print("-" * 72)
    print(f"{'Total pasivos':<54}{_money(float(data['total_pasivos'])):>18}")

    print("\nCapital")
    print("-" * 72)
    for item in data["capital"]:
        print(f"{item['codigo']:<10}{item['nombre']:<44}{_money(float(item['monto'])):>18}")
    print("-" * 72)
    print(f"{'Total capital':<54}{_money(float(data['total_capital'])):>18}")

    print("=" * 72)
    print(f"{'Pasivo + Capital':<54}{_money(float(data['pasivo_mas_capital'])):>18}")
