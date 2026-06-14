# Proyectos Personales — Auditoría, Análisis de Datos y Machine Learning

Profesional de **auditoría en transición hacia Data Analytics y Data Science**,
combinando experiencia en control interno y calidad de datos con herramientas
modernas de análisis, machine learning y business intelligence.

Portfolio de proyectos de datos construido como una **progresión deliberada**: cada
proyecto suma una capa de dificultad técnica sobre el anterior, partiendo del análisis
descriptivo y avanzando hacia lo predictivo, la nube y la automatización.

El hilo conductor es mi perfil de **auditor**: en todos los proyectos, antes de
modelar o visualizar, audito la integridad de los datos y documento qué se excluye,
cuánto y por qué. Estado declarado y evidencia no siempre coinciden — y eso se
verifica, no se asume.

---

## 🧭 Ruta de aprendizaje y evolución técnica

| # | Proyecto | Foco | Salto técnico que incorpora | Estado |
|---|----------|------|------------------------------|--------|
| 1 | Ecommerce Customer Analytics | Análisis descriptivo + segmentación | SQL avanzado, RFM, K-Means no supervisado | ✅ Publicado |
| 2 | Dashboard Logístico (Tableau) | Business Intelligence | Pipeline reproducible Python→Tableau, data storytelling | ✅ Publicado |
| 3 | Auditoría Continua ISO 27001 | Ingeniería + ciberseguridad | Docker, PostgreSQL, CI/CD, deploy en AWS, alertas, Power BI · Tableau | 🚧 En desarrollo |
| 4 | Clasificador de Sentimiento (PNL) | Machine Learning supervisado | TF-IDF, regresión logística, deploy como API | 📋 Planificado |
| 5 | Monitor BOCBA | Proyecto original end-to-end | Web scraping (Playwright), clasificación de normativa | 📋 Planificado |

De **describir** datos (P1-P2) a **predecir** con ellos (P4), pasando por
**industrializar** el proceso (P3) y resolver un problema **propio y real** (P5).

---

## 📂 Proyectos

### 1 · [Ecommerce Customer Analytics](01-ecommerce-customer-analytics) ✅
Segmentación RFM y clustering K-Means sobre **Online Retail II** (1M+ transacciones,
retail UK). Limpieza auditada en Python, persistencia en SQLite, métricas RFM con
CTEs en SQL, análisis de cohortes y validación del modelo no supervisado contra
reglas de negocio.

**Insight destacado:** el K-Means reveló 650 clientes "leales" que acumulan £3,1M
históricos pero llevaban ~7 meses inactivos — un segmento de reactivación prioritario
que las reglas tradicionales escondían.

`Python` · `Pandas` · `SQL (SQLite)` · `Scikit-Learn` · `Matplotlib/Seaborn`

### 2 · [Dashboard Logístico — Tableau](02-dashboard-logistica-tableau) ✅
Análisis de la cadena de entrega de **Olist** (~100k pedidos, 9 tablas). Pipeline
reproducible en Pandas (`data_preparation.py`) que alimenta un dashboard interactivo
en Tableau Public. Arquitectura de dos capas: **Python prepara, Tableau presenta**,
versionadas juntas.

**Insight destacado:** velocidad y confiabilidad son dos dimensiones distintas
de la logística. Algunos estados tardan más por distancia pero cumplen el plazo
prometido, mientras otros fallan en el cumplimiento por razones diferentes. El
dashboard separa ambas para no confundirlas.

🔗 [Ver dashboard en Tableau Public](https://public.tableau.com/app/profile/eduardo.govea/viz/DashboardLogsticoOlist/DashboardLogsticoOlistEntregasenBrasil2017-2018)

> 🔧 **Próxima mejora:** documentar el pipeline end-to-end en el README —
> mostrar de forma explícita el flujo *Python prepara los datos → Tableau los
> visualiza*, con el script de preparación y el dashboard versionados juntos.

`Python` · `Pandas` · `Tableau Public`

### 3 · Auditoría Continua ISO 27001 🚧 En desarrollo
Generador de logs de acceso sintéticos con anomalías inyectadas (accesos post-baja,
horarios anómalos, escalamiento de privilegios) + motor de detección de no
conformidades ISO 27001 + alertas por mail. Pensado como sistema industrializado,
no como notebook.

`Python` · `PostgreSQL` · `Docker` · `pytest` · `GitHub Actions` · `Power BI` · `AWS (EC2)`

### 4 · Clasificador de Sentimiento — PNL 📋
Clasificación de ~100k reseñas reales de Olist (portugués) en positivas/negativas.
El puntaje de estrellas provee las etiquetas → aprendizaje supervisado, complemento
del K-Means no supervisado del P1. Énfasis en el análisis de errores: dónde y por qué
falla un modelo lineal.

`Python` · `Scikit-Learn` · `TF-IDF` · `Regresión Logística` · (opcional: `Hugging Face`)

### 5 · Monitor BOCBA 📋
Proyecto 100% original, nacido de un problema laboral real: scraping del Boletín
Oficial de la Ciudad de Buenos Aires con Playwright (resolviendo el WAF de F5 BIG-IP,
documentado como desafío técnico) y clasificación de normativa por relevancia.

`Python` · `Playwright` · `PNL`

---

## 🛠️ Stack general

**Lenguajes y datos:** Python, SQL (SQLite / PostgreSQL)
**Análisis y ML:** Pandas, NumPy, Scikit-Learn
**Visualización / BI:** Tableau, Power BI, Matplotlib, Seaborn
**Ingeniería:** Docker, pytest, GitHub Actions, AWS
**Gestión:** Git, GitHub, Jira

## 👤 Autor

**Eduardo Govea** — Auditoría · Análisis de Datos · Machine Learning
🔗 [LinkedIn](https://www.linkedin.com/in/eduardo-luis-govea) · [Tableau Public](https://public.tableau.com/app/profile/eduardo.govea)
