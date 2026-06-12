"""
Proyecto 2 - Dashboard Logístico Olist
Pipeline de preparación de datos para Tableau.
Lee los CSVs crudos de data/, filtra, calcula métricas logísticas
y exporta data/pedidos_logistica.csv.
"""

import os
import pandas as pd

# ==================================================
# CONFIGURACIÓN DE RUTAS (CONTROL DE ENTORNO)
# ==================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

ARCHIVO_SALIDA = os.path.join(DATA_DIR, "pedidos_logistica.csv")

COLUMNAS_FECHA = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]


def cargar_tablas() -> dict:
    """Carga los CSVs necesarios desde data/."""
    rutas = {
        "orders": "olist_orders_dataset.csv",
        "customers": "olist_customers_dataset.csv",
        "order_items": "olist_order_items_dataset.csv",
    }
    return {
        nombre: pd.read_csv(os.path.join(DATA_DIR, archivo))
        for nombre, archivo in rutas.items()
    }


def preparar_pedidos(orders: pd.DataFrame) -> pd.DataFrame:
    """Convierte fechas, filtra entregados con fecha y calcula métricas.

    Hallazgos de calidad documentados:
    - 8 pedidos 'delivered' sin fecha de entrega -> excluidos.
    - 6 pedidos 'canceled' con fecha de entrega -> excluidos (manda el estado).
    - Lote de pedidos cerrados masivamente el 19/09/2017 -> se conservan,
      explican parte de los outliers >100 días.
    """
    for col in COLUMNAS_FECHA:
        orders[col] = pd.to_datetime(orders[col])

    entregados = orders[
        (orders["order_status"] == "delivered")
        & (orders["order_delivered_customer_date"].notna())
    ].copy()

    entregados["dias_entrega"] = (
        entregados["order_delivered_customer_date"] - entregados["order_purchase_timestamp"]
    ).dt.days
    entregados["dias_prometidos"] = (
        entregados["order_estimated_delivery_date"] - entregados["order_purchase_timestamp"]
    ).dt.days
    entregados["dias_vs_promesa"] = (
        entregados["order_delivered_customer_date"] - entregados["order_estimated_delivery_date"]
    ).dt.days
    entregados["entrega_a_tiempo"] = entregados["dias_vs_promesa"] <= 0
    return entregados


def agregar_cliente(entregados: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    """Incorpora estado y ciudad del cliente."""
    clientes = customers[["customer_id", "customer_city", "customer_state"]]
    return entregados.merge(clientes, on="customer_id", how="left")


def agregar_flete(entregados: pd.DataFrame, order_items: pd.DataFrame) -> pd.DataFrame:
    """Agrega ítems, valor de productos y costo de flete por pedido."""
    flete = order_items.groupby("order_id").agg(
        items=("order_item_id", "count"),
        valor_productos=("price", "sum"),
        costo_flete=("freight_value", "sum"),
    ).reset_index()
    return entregados.merge(flete, on="order_id", how="left")


def construir_tabla_final(entregados: pd.DataFrame) -> pd.DataFrame:
    """Selecciona columnas, renombra al español y segmenta entregas."""
    tabla = entregados[[
        "order_id", "order_purchase_timestamp", "order_delivered_customer_date",
        "order_estimated_delivery_date", "customer_state", "customer_city",
        "dias_entrega", "dias_prometidos", "dias_vs_promesa", "entrega_a_tiempo",
        "items", "valor_productos", "costo_flete",
    ]].rename(columns={
        "order_id": "id_pedido",
        "order_purchase_timestamp": "fecha_compra",
        "order_delivered_customer_date": "fecha_entrega",
        "order_estimated_delivery_date": "fecha_prometida",
        "customer_state": "estado",
        "customer_city": "ciudad",
        "items": "cantidad_items",
    })
    tabla["segmento_entrega"] = pd.cut(
        tabla["dias_entrega"],
        bins=[-1, 7, 15, 30, 999],
        labels=["Rápida (0-7)", "Normal (8-15)", "Lenta (16-30)", "Crítica (>30)"],
    )
    return tabla


def main():
    tablas = cargar_tablas()
    entregados = preparar_pedidos(tablas["orders"])
    entregados = agregar_cliente(entregados, tablas["customers"])
    entregados = agregar_flete(entregados, tablas["order_items"])
    tabla_final = construir_tabla_final(entregados)

    tabla_final.to_csv(ARCHIVO_SALIDA, index=False)
    print(f"Exportado {ARCHIVO_SALIDA}: {len(tabla_final)} filas, {len(tabla_final.columns)} columnas")
    print(f"Demora promedio: {tabla_final['dias_entrega'].mean():.1f} días")
    print(f"% entregas a tiempo: {tabla_final['entrega_a_tiempo'].mean()*100:.1f}%")


if __name__ == "__main__":
    main()