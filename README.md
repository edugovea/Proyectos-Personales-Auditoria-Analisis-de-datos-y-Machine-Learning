# Proyectos Personales — Auditoría, Análisis de Datos y Machine Learning

Profesional de auditoría en transición hacia Data Analytics y Data Science, combinando experiencia en control interno y calidad de datos con herramientas modernas de análisis, machine learning y business intelligence.

Portfolio de proyectos de datos construido como una progresión deliberada: cada proyecto suma una capa de dificultad técnica sobre el anterior, partiendo del análisis descriptivo y avanzando hacia lo predictivo, la nube y la automatización.

El hilo conductor es mi perfil de auditor: en todos los proyectos, antes de modelar o visualizar, audito la integridad de los datos y documento qué se excluye, cuánto y por qué. Estado declarado y evidencia no siempre coinciden — y eso se verifica, no se asume.

## 🧭 Ruta de aprendizaje y evolución técnica

| # | Proyecto | Foco | Salto técnico que incorpora | Estado |
|---|----------|------|------------------------------|--------|
| 1 | Ecommerce Customer Analytics | Análisis descriptivo + segmentación | SQL avanzado, RFM, K-Means no supervisado | ✅ Publicado |
| 2 | Dashboard Logístico (Tableau) | Business Intelligence | Pipeline reproducible Python→Tableau, data storytelling | ✅ Publicado |
| 3 | Auditoría Continua ISO 27001 | Ingeniería de datos + ciberseguridad | PostgreSQL (functions, stored procedures), trigger de inmutabilidad, motor de detección, Power BI | 🚧 En desarrollo |
| 4 | Clasificador de Sentimiento (PNL) | Machine Learning supervisado | TF-IDF, regresión logística, análisis de errores profundo | 📋 Planificado |
| 5 | Monitor BOCBA | Sistema end-to-end en producción | Web scraping (Playwright), clasificación con LLM/embeddings, alertas, Docker, AWS, GitHub Actions | 📋 Planificado |

De describir datos (P1-P2) a predecir con ellos (P4), pasando por industrializar la detección (P3) y llevar a producción un sistema propio en la nube (P5).

## 📂 Proyectos

### 1 · Ecommerce Customer Analytics ✅

Segmentación RFM y clustering K-Means sobre Online Retail II (1M+ transacciones, retail UK). Limpieza auditada en Python, persistencia en SQLite, métricas RFM con CTEs en SQL, análisis de cohortes y validación del modelo no supervisado contra reglas de negocio.

**Insight destacado:** el K-Means reveló 650 clientes "leales" que acumulan £3,1M históricos pero llevaban ~7 meses inactivos — un segmento de reactivación prioritario que las reglas tradicionales escondían.

`Python` · `Pandas` · `SQL (SQLite)` · `Scikit-Learn` · `Matplotlib/Seaborn`

### 2 · Dashboard Logístico — Tableau ✅

Análisis de la cadena de entrega de Olist (~100k pedidos, 9 tablas). Pipeline reproducible en Pandas (`data_preparation.py`) que alimenta un dashboard interactivo en Tableau Public. Arquitectura de dos capas: Python prepara, Tableau presenta, versionadas juntas.

**Insight destacado:** velocidad y confiabilidad son dos dimensiones distintas de la logística. Algunos estados tardan más por distancia pero cumplen el plazo prometido, mientras otros fallan en el cumplimiento por razones diferentes. El dashboard separa ambas para no confundirlas.

🔗 Ver dashboard en Tableau Public

🔧 **Próxima mejora:** documentar el pipeline end-to-end en el README — mostrar de forma explícita el flujo Python prepara los datos → Tableau los visualiza, con el script de preparación y el dashboard versionados juntos.

`Python` · `Pandas` · `Tableau Public`

### 3 · Auditoría Continua ISO 27001 🚧 En desarrollo

Sistema de detección de no conformidades ISO 27001 sobre logs de acceso. Un generador produce eventos de acceso sintéticos **realistas — con ruido y casos ambiguos, no anomalías limpias** — e inyecta cuatro tipos de incumplimiento (acceso post-baja, horario anómalo, escalamiento de privilegios, violación de segregación de funciones), cada uno mapeado a su control del Anexo A de ISO 27001:2022. Un motor en PostgreSQL (functions + stored procedures) detecta esas no conformidades y las registra como hallazgos con severidad y trazabilidad completa.

El núcleo del proyecto es el criterio de auditor, no la infraestructura:

- **Trigger de inmutabilidad** sobre la tabla de hallazgos: una vez registrado, un hallazgo no se puede modificar ni borrar. Es el control de integridad de la evidencia de auditoría, garantizado en la capa de datos.
- **Mapeo anomalía → control ISO** (A.5.18, A.8.16, A.8.2, A.5.3): detección con sentido de cumplimiento, no logs aleatorios.
- **Severidad y trazabilidad** del hallazgo (`finding_id`, `control_iso`, `severidad`, `evidencia`, `estado`): permite mostrar el ciclo de vida completo del hallazgo.
- **Validación rigurosa:** el generador guarda la verdad conocida (ground truth) por separado; los tests verifican que el motor detecta sin falsos negativos y maneja los casos ambiguos.

Pensado como sistema industrializado, no como notebook de análisis. Dashboards en Power BI cierran el proyecto.

`Python` · `PostgreSQL` · `pytest` · `Power BI`

### 4 · Clasificador de Sentimiento — PNL 📋

Clasificación de ~100k reseñas reales de Olist (portugués) en positivas/negativas. El puntaje de estrellas provee las etiquetas → aprendizaje supervisado, complemento del K-Means no supervisado del P1.

El valor del proyecto no está en la métrica de accuracy, sino en el **análisis de errores profundo**: agrupar las fallas del modelo por patrón (sarcasmo, reseñas mixtas, portugués coloquial) y documentar *dónde y por qué* un modelo lineal no las captura. Opcionalmente, comparar contra un transformer (Hugging Face) para evidenciar el contraste.

`Python` · `Scikit-Learn` · `TF-IDF` · `Regresión Logística` · (opcional: `Hugging Face`)

### 5 · Monitor BOCBA 📋

Proyecto 100% original, nacido de un problema laboral real: un sistema que monitorea el Boletín Oficial de la Ciudad de Buenos Aires, identifica la normativa relevante y avisa automáticamente. Es la carta de ingeniería de sistemas del portfolio: vive en producción, corre solo y la infraestructura responde a una necesidad genuina.

- **Scraping con Playwright**, resolviendo el WAF de F5 BIG-IP (documentado como desafío técnico) + consumo de la API REST del Boletín.
- **Clasificación de relevancia con LLM/embeddings:** en lugar de filtrar por keywords, el sistema entiende semánticamente cada publicación, decide si es relevante y genera un resumen.
- **Alertas:** cuando aparece normativa relevante, llega un mail con el resumen generado, no solo el enlace.
- **AWS:** el monitor corre 24/7 desplegado en la nube (EC2 / Lambda + EventBridge).
- **GitHub Actions:** orquesta las corridas programadas y los tests.
- **Docker:** el sistema se contenedoriza para desplegarlo de forma reproducible en la nube.

`Python` · `Playwright` · `LLM / embeddings` · `Docker` · `AWS` · `GitHub Actions`

## 🛠️ Stack general

**Lenguajes y datos:** Python, SQL (SQLite / PostgreSQL)
**Análisis y ML:** Pandas, NumPy, Scikit-Learn, LLM / embeddings
**Visualización / BI:** Tableau, Power BI, Matplotlib, Seaborn
**Ingeniería:** Docker, pytest, GitHub Actions, AWS
**Gestión:** Git, GitHub, Jira

## 👤 Autor

Eduardo Govea — Auditoría · Análisis de Datos · Machine Learning
🔗 LinkedIn · Tableau Public
