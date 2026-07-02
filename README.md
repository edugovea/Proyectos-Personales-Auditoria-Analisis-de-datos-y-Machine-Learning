# Proyectos Personales — Auditoría, Análisis de Datos y Machine Learning

Profesional de auditoría en transición hacia Data Analytics y Data Science, combinando experiencia en control interno y calidad de datos con herramientas modernas de análisis, machine learning y business intelligence.

Portfolio de proyectos de datos construido como una progresión deliberada: cada proyecto suma una capa de dificultad técnica sobre el anterior, partiendo del análisis descriptivo y avanzando hacia lo predictivo, la nube y la automatización.

El hilo conductor es mi perfil de auditor: en todos los proyectos, antes de modelar o visualizar, audito la integridad de los datos y documento qué se excluye, cuánto y por qué. Estado declarado y evidencia no siempre coinciden — y eso se verifica, no se asume.

## 🧭 Ruta de aprendizaje y evolución técnica

| # | Proyecto | Foco | Salto técnico que incorpora | Estado |
|---|----------|------|------------------------------|--------|
| 1 | Ecommerce Customer Analytics | Análisis descriptivo + segmentación | SQL avanzado, RFM, K-Means no supervisado | ✅ Publicado |
| 2 | Dashboard Logístico (Tableau) | Business Intelligence | Pipeline reproducible Python→Tableau, data storytelling | ✅ Publicado |
| 3 | Auditoría Continua ISO 27001 | Ingeniería de datos + auditoría TI | PostgreSQL, SQL functions, trigger de inmutabilidad, pytest, Power BI | ✅ Completo |
| 4 | Clasificador de Sentimiento (PNL) | Machine Learning supervisado | TF-IDF, regresión logística, análisis de errores profundo | 📋 Planificado |
| 5 | Monitor Normativo BOCBA | Automatización + procesamiento documental | Consumo de API pública, extracción de texto de PDFs (PyMuPDF), matriz de riesgo por materia, tablero Streamlit, gacetillas PDF automatizadas; evolución: feedback del auditor → ML | ✅ Funcional — en evolución |
| 6 | Auditoría Continua de IA + Seguridad | AI Assurance + seguridad | AI assurance de un modelo ML (SHAP, drift, model card, fairness) + DevSecOps (SAST, escaneo de dependencias, log con hash-chaining); mapeo a ISO/IEC 42001 y NIST AI RMF | 📋 Planificado |

La ruta del portfolio avanza desde análisis descriptivo y visualización ejecutiva (P1-P2), hacia detección industrializada con trazabilidad de auditoría (P3), modelos predictivos/NLP (P4), automatización aplicada a una fuente pública real (P5) y aseguramiento de modelos de IA con seguridad (P6).

**Linajes entre proyectos:**
- **P2 → P4** (dataset Olist): el P2 *describe* la operación con BI; el P4 da el salto al *modelado predictivo* (NLP) sobre el mismo dataset.
- **P3 → P6** (auditoría): el motor de auditoría continua sobre datos sintéticos del P3 evoluciona hacia AI Assurance + seguridad en el P6.

## 📂 Proyectos

### 1 · Ecommerce Customer Analytics ✅

Segmentación RFM y clustering K-Means sobre Online Retail II (1M+ transacciones, retail UK). Limpieza auditada en Python, persistencia en SQLite, métricas RFM con CTEs en SQL, análisis de cohortes y validación del modelo no supervisado contra reglas de negocio.

**Insight destacado:** el K-Means reveló 650 clientes "leales" que acumulan £3,1M históricos pero llevaban ~7 meses inactivos — un segmento de reactivación prioritario que las reglas tradicionales escondían.

`Python` · `Pandas` · `SQL (SQLite)` · `Scikit-Learn` · `Matplotlib/Seaborn`

### 2 · Dashboard Logístico — Tableau ✅

Dashboard interactivo en Tableau Public para analizar la cadena de entrega de Olist (~100.000 pedidos, 9 tablas). El proyecto utiliza un pipeline reproducible en Python/Pandas (`data_preparation.py`) que consolida los datos logísticos y genera la tabla final utilizada por Tableau.

Arquitectura de dos capas: **Python prepara los datos, Tableau los presenta**. El script de preparación, la documentación del pipeline y el dashboard quedan versionados juntos, asegurando trazabilidad entre transformación de datos e insights visuales.

**Insight destacado:** velocidad y confiabilidad logística no son lo mismo. El dashboard separa tiempos reales de entrega y cumplimiento de promesa para identificar problemas distintos según estado/región.

🔗 **[Ver dashboard en Tableau Public](https://public.tableau.com/app/profile/eduardo.govea/viz/DashboardLogsticoOlist/DashboardLogsticoOlistEntregasenBrasil2017-2018)**

> 🔗 **Evolución:** el mismo dataset Olist se retoma en el **Proyecto 4**, dando el salto de la visualización descriptiva (BI) al modelado predictivo (NLP).

`Python` · `Pandas` · `Tableau Public`

### 3 · Auditoría Continua ISO 27001 ✅ Completo

Sistema de auditoría continua sobre logs de acceso sintéticos, orientado a detectar posibles no conformidades vinculadas a controles de ISO 27001:2022. El proyecto combina generación de eventos, motor de detección en PostgreSQL, trazabilidad de hallazgos y validación automatizada con `pytest`.

El generador produce logs realistas con ruido operativo y casos ambiguos, no anomalías limpias. Sobre esos eventos se inyectan cuatro tipos de incumplimiento: acceso post-baja, horario anómalo, escalamiento de privilegios y violación de segregación de funciones. Cada anomalía queda mapeada a un control del Anexo A de ISO 27001:2022 (A.5.18, A.8.16, A.8.2, A.5.3).

El núcleo del proyecto es el criterio de auditoría aplicado a datos:

- **Motor SQL en PostgreSQL:** funciones de detección y orquestación para registrar hallazgos.
- **Tabla `findings`:** registro de hallazgos con severidad, evidencia, estado y trazabilidad.
- **Trigger de inmutabilidad:** una vez registrado, un hallazgo no puede modificarse ni eliminarse.
- **Mapeo anomalía → control ISO:** detección con sentido de cumplimiento, no solo análisis técnico de logs.
- **Tests automatizados:** validación del motor contra la verdad conocida generada por el generador, sin falsos positivos ni negativos sobre el ruido.
- **Dashboards Power BI:** vista ejecutiva (KPIs y agregados por control/severidad/estado) y vista operativa (detalle por hallazgo con filtros), conectadas por *Import* a dos vistas SQL.

El proyecto se gestiona con un tablero Kanban en Jira, siguiendo un proceso deliberado: arquitectura → backlog → diseño → implementación → validación.

> 🔗 **Evolución:** este motor de auditoría continua es la base del **Proyecto 6** (AI Assurance + seguridad).

*Estado: completo (MVP). Motor SQL, generador, trigger de inmutabilidad, tests y dashboards Power BI finalizados y documentados.*

`Python` · `PostgreSQL` · `pytest` · `Power BI` · `Jira`

### 4 · Clasificador de Sentimiento — PNL 📋

**Evolución del Proyecto 2 sobre el mismo dataset Olist.** Si el P2 *describe* la operación logística con BI, el P4 da el salto al *modelado predictivo*: clasifica ~100k reseñas reales de Olist (portugués) en positivas/negativas, usando el puntaje de estrellas como etiqueta (aprendizaje supervisado).

El valor del proyecto no está en la métrica de accuracy, sino en el **análisis de errores profundo**: agrupar las fallas del modelo por patrón (sarcasmo, reseñas mixtas, portugués coloquial) y documentar *dónde y por qué* un modelo lineal no las captura. Opcionalmente, comparar contra un transformer (Hugging Face) para evidenciar el contraste.

`Python` · `Scikit-Learn` · `TF-IDF` · `Regresión Logística` · (opcional: `Hugging Face`)

### 5 · Monitor Normativo BOCBA ✅ Funcional — en evolución

Proyecto original nacido de un problema laboral real: vigilancia y búsqueda de normativa del Boletín Oficial de la Ciudad de Buenos Aires sobre **fuentes públicas** (API REST oficial), con criterio de relevancia explicable orientado a auditoría. Es la carta de automatización del portfolio.

- **Motor de vigilancia**: consume la API del Boletín, descarga los PDFs en paralelo (caché + reintentos), extrae texto con PyMuPDF y clasifica con una **matriz de riesgo por materia** calibrada con criterios reales de un área legal.
- **Tablero Streamlit**: búsqueda por fecha, tema, palabra libre o número de boletín (con descarga en vivo del histórico — comprobado hasta 2022), tabla tipo Excel, y **automatización diaria** vía Programador de tareas desde la propia interfaz.
- **Salidas**: reporte JSON, informe ejecutivo PDF, gacetilla completa y **edición institucional curada** lista para circular.
- *Evolución prevista:* botón de feedback del auditor → dataset etiquetado → clasificador ML con fallback a reglas.

> Proyecto personal y educativo, basado en información pública. No es una herramienta oficial del Gobierno de la Ciudad. Interfaz desarrollada con asistencia de IA (detalle en el README del proyecto).

`Python` · `Requests` · `PyMuPDF` · `ReportLab` · `Streamlit` · `AgGrid` · `Git/GitHub` · *(evolución: `scikit-learn` · `embeddings`)*

### 6 · Auditoría Continua de IA + Seguridad 📋

**Continuación y evolución del Proyecto 3.** Toma el motor de auditoría continua del P3 —sobre la misma base de datos inventada (logs sintéticos con *ground truth*)— y lo lleva a **AI Assurance + seguridad**: el sistema deja de auditar solo controles y pasa a auditar también un **modelo de machine learning**, dentro de una envoltura de controles de ciberseguridad.

Tres capas incrementales, cada una construible y defendible por separado:

- **Seguridad (DevSecOps):** SAST en CI (bandit), escaneo de dependencias (pip-audit) y log de auditoría a prueba de manipulación (encadenamiento de hashes), extendiendo el trigger de inmutabilidad del P3. Mapea a ISO 27001 A.8.15 / A.8.16 / A.8.28.
- **ML:** detección de anomalías sobre los logs de acceso sintéticos (Isolation Forest) — analítica de seguridad.
- **AI Assurance:** auditoría del propio modelo — explicabilidad (SHAP), linaje de datos, monitoreo de drift, chequeo de sesgo y *model card*. Mapeo a ISO/IEC 42001 y NIST AI RMF.

> 🔗 **Base:** se construye sobre el Proyecto 3 (motor, esquema y datos sintéticos), no desde cero.

*Estado: planificado. Documento de diseño definido; implementación por capas pendiente.*

`Python` · `PostgreSQL` · `pytest` · `bandit` · `Scikit-Learn` · `SHAP` · `Power BI` · *(marcos: ISO/IEC 42001 · NIST AI RMF)*

## 🛠️ Stack general

**Lenguajes y datos:** Python, SQL (SQLite / PostgreSQL)
**Análisis y ML:** Pandas, NumPy, Scikit-Learn · *(próximamente: LLM / embeddings)*
**Visualización / BI:** Tableau, Power BI, Matplotlib, Seaborn
**Ingeniería:** Docker, pytest · *(previstos para P5/P6: GitHub Actions/CI, AWS)*
**Gestión:** Git, GitHub, Jira

## 👤 Autor

Eduardo Govea — Auditoría · Análisis de Datos · Machine Learning
🔗 LinkedIn · Tableau Public
