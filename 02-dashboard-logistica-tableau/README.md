# 📦 Dashboard Logístico Olist — Entregas en Brasil 2017-2018

Dashboard interactivo en Tableau Public para monitorear la cadena de entrega del
e-commerce brasileño Olist: tiempos reales vs prometidos, demoras por región,
segmentación de entregas y costos de flete.

🔗 **[Ver dashboard interactivo en Tableau Public](https://public.tableau.com/app/profile/eduardo.govea/viz/DashboardLogsticoOlist/DashboardLogsticoOlistEntregasenBrasil2017-2018)**

![Dashboard Logístico Olist](img/dashboard.png)

## 🎯 Objetivo

Convertir ~100.000 pedidos distribuidos en 9 tablas relacionales en un panel que
responda en 30 segundos las preguntas clave de un gerente de logística:
¿cuánto tardamos en entregar?, ¿cumplimos lo que prometemos?, ¿dónde están los
problemas? y ¿cómo evolucionamos en el tiempo?

## 🛠️ Stack

- **Python / Pandas** — limpieza, joins y cálculo de métricas (capa de datos)
- **Tableau Public** — visualización e interactividad (capa de presentación)
- **Dataset:** [Brazilian E-Commerce Public Dataset by Olist (Kaggle)](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)

## ⚙️ Pipeline de datos

`data_preparation.py` ejecuta el proceso completo de forma reproducible:

1. Carga las tablas crudas (`orders`, `customers`, `order_items`)
2. Convierte timestamps y filtra pedidos entregados con fecha válida
3. Calcula métricas logísticas: días de entrega, días prometidos, desvío vs
   promesa y flag de entrega a tiempo
4. Incorpora dimensión geográfica (estado/ciudad del cliente) y costos
   (flete y valor de productos por pedido)
5. Segmenta las entregas (Rápida / Normal / Lenta / Crítica) y exporta una
   única tabla plana en español (`pedidos_logistica.csv`) lista para Tableau

**Reproducir:** descargar el dataset de Kaggle, descomprimir los CSV en `data/`
y ejecutar `python data_preparation.py`.

La exploración que fundamenta cada decisión del pipeline está documentada en
`01_exploracion.ipynb`.

## 🔍 Hallazgos de calidad de datos

Con mirada de auditor, antes de visualizar se verificó la consistencia interna
del dataset. Hallazgos:

| # | Hallazgo | Tratamiento |
|---|----------|-------------|
| 1 | 8 pedidos en estado `delivered` **sin fecha de entrega** (uno sin siquiera fecha de despacho) | Excluidos de las métricas de tiempo |
| 2 | 6 pedidos `canceled` **con fecha de entrega** (4 de fines de 2016) | Permanecen como cancelados: el estado final del negocio prevalece |
| 3 | 7 de los 10 pedidos más demorados fueron "entregados" el **mismo día (19/09/2017)** con compras de feb-mar: patrón de cierre administrativo masivo, no entregas reales | Se conservan y documentan: explican parte de los outliers >100 días |
| 4 | Los meses de 2016 tienen volúmenes mínimos (cientos de pedidos vs ~4.000/mes después) que distorsionan los promedios | 2016 filtrado de la serie temporal |

Lección general: estado declarado y timestamps pueden contradecirse; los
filtros del pipeline combinan ambos (estado **y** fecha) en lugar de confiar
en un solo campo.

## 📈 Insights principales

- **Brecha geográfica:** São Paulo recibe en 8,3 días promedio; Roraima en 29.
  El norte amazónico y el nordeste concentran las mayores demoras.
- **Velocidad ≠ confiabilidad:** los estados remotos (RR, AP, AM) son lentos
  pero cumplen la promesa (>87% a tiempo) porque Olist les promete plazos más
  largos; Alagoas, en cambio, combina demora alta con la peor tasa de
  cumplimiento (78,6%). Son dos problemas distintos que el dashboard separa.
- **Crisis y recuperación:** la demora saltó a 15-16 días entre nov-2017 y
  mar-2018 (Black Friday + fiestas) y luego mejoró de forma sostenida hasta
  ~7 días a mediados de 2018: Olist duplicó su velocidad de entrega en un año.
- **Distribución general:** 93,2% de entregas a tiempo; solo 4,3% de pedidos
  superan los 30 días (segmento crítico).

