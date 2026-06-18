"""
Proyecto 2 - Dashboard Logístico Olist
Pipeline de preparación de datos para Tableau.

Lee los CSVs crudos desde data/, valida insumos mínimos, calcula métricas
logísticas y exporta data/pedidos_logistica.csv.
"""

from pathlib import Path

import pandas as pd


# ==================================================
# CONFIGURACIÓN DE RUTAS
# ==================================================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ARCHIVO_SALIDA = DATA_DIR / "pedidos_logistica.csv"

ARCHIVOS_REQUERIDOS = {
    "orders": "olist_orders_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
}

COLUMNAS_FECHA = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]


def validar_archivos_requeridos() -> None:
    """Validate that all required source files exist before running the pipeline."""
    faltantes = [
        archivo
        for archivo in ARCHIVOS_REQUERIDOS.values()
        if not (DATA_DIR / archivo).exists()
    ]

    if faltantes:
        detalle = "\n".join(f"- {archivo}" for archivo in faltantes)
        raise FileNotFoundError(
            "No se encontraron los siguientes archivos requeridos en la carpeta data/:\n"
            f"{detalle}\n\n"
            "Descargá el dataset de Kaggle y colocá los CSVs requeridos dentro de data/."
        )


def cargar_tablas() -> dict[str, pd.DataFrame]:
    """Load required CSV files from the data directory."""
    validar_archivos_requeridos()

    return {
        nombre: pd.read_csv(DATA_DIR / archivo)
        for nombre, archivo in ARCHIVOS_REQUERIDOS.items()
    }


def preparar_pedidos(orders: pd.DataFrame) -> pd.DataFrame:
    """Convert dates, filter delivered orders and calculate logistics metrics.

    Hallazgos de calidad documentados:
    - 8 pedidos 'delivered' sin fecha de entrega -> excluidos.
    - 6 pedidos 'canceled' con fecha de entrega -> excluidos porque prevalece el estado.
    - Lote de pedidos cerrados masivamente el 19/09/2017 -> se conservan como outliers.
    """
    orders = orders.copy()

    for column in COLUMNAS_FECHA:
        orders[column] = pd.to_datetime(orders[column], errors="coerce")

    entregados = orders[
        (orders["order_status"] == "delivered")
        & (orders["order_delivered_customer_date"].notna())
    ].copy()

    entregados["dias_entrega"] = (
        entregados["order_delivered_customer_date"]
        - entregados["order_purchase_timestamp"]
    ).dt.days

    entregados["dias_prometidos"] = (
        entregados["order_estimated_delivery_date"]
        - entregados["order_purchase_timestamp"]
    ).dt.days

    entregados["dias_vs_promesa"] = (
        entregados["order_delivered_customer_date"]
        - entregados["order_estimated_delivery_date"]
    ).dt.days

    entregados["entrega_a_tiempo"] = entregados["dias_vs_promesa"] <= 0

    return entregados


def agregar_cliente(entregados: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    """Add customer geographic information."""
    clientes = customers[["customer_id", "customer_city", "customer_state"]].copy()

    return entregados.merge(clientes, on="customer_id", how="left")


def agregar_flete(entregados: pd.DataFrame, order_items: pd.DataFrame) -> pd.DataFrame:
    """Aggregate item count, product value and freight cost by order."""
    flete = (
        order_items.groupby("order_id")
        .agg(
            items=("order_item_id", "count"),
            valor_productos=("price", "sum"),
            costo_flete=("freight_value", "sum"),
        )
        .reset_index()
    )

    return entregados.merge(flete, on="order_id", how="left")


def construir_tabla_final(entregados: pd.DataFrame) -> pd.DataFrame:
    """Select final columns, rename them in Spanish and classify delivery segments."""
    columnas_finales = [
        "order_id",
        "order_purchase_timestamp",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
        "customer_state",
        "customer_city",
        "dias_entrega",
        "dias_prometidos",
        "dias_vs_promesa",
        "entrega_a_tiempo",
        "items",
        "valor_productos",
        "costo_flete",
    ]

    tabla = entregados[columnas_finales].rename(
        columns={
            "order_id": "id_pedido",
            "order_purchase_timestamp": "fecha_compra",
            "order_delivered_customer_date": "fecha_entrega",
            "order_estimated_delivery_date": "fecha_prometida",
            "customer_state": "estado",
            "customer_city": "ciudad",
            "items": "cantidad_items",
        }
    )

    tabla["segmento_entrega"] = pd.cut(
        tabla["dias_entrega"],
        bins=[-1, 7, 15, 30, 999],
        labels=["Rápida (0-7)", "Normal (8-15)", "Lenta (16-30)", "Crítica (>30)"],
    )

    return tabla


def exportar_tabla(tabla_final: pd.DataFrame) -> None:
    """Export the final analytical table used by Tableau."""
    DATA_DIR.mkdir(exist_ok=True)
    tabla_final.to_csv(ARCHIVO_SALIDA, index=False)


def imprimir_resumen(tabla_final: pd.DataFrame) -> None:
    """Print a simple execution summary for traceability."""
    print(
        f"Exportado {ARCHIVO_SALIDA}: "
        f"{len(tabla_final)} filas, {len(tabla_final.columns)} columnas"
    )
    print(f"Demora promedio: {tabla_final['dias_entrega'].mean():.1f} días")
    print(f"% entregas a tiempo: {tabla_final['entrega_a_tiempo'].mean() * 100:.1f}%")


def main() -> None:
    """Run the full Python-to-Tableau data preparation pipeline."""
    tablas = cargar_tablas()

    entregados = preparar_pedidos(tablas["orders"])
    entregados = agregar_cliente(entregados, tablas["customers"])
    entregados = agregar_flete(entregados, tablas["order_items"])

    tabla_final = construir_tabla_final(entregados)

    exportar_tabla(tabla_final)
    imprimir_resumen(tabla_final)


if __name__ == "__main__":
    main()
