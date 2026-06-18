# Proyectos Personales — Auditoría, Análisis de Datos y Machine Learning

Profesional de auditoría en transición hacia Data Analytics y Data Science, combinando experiencia en control interno y calidad de datos con herramientas modernas de análisis, machine learning y business intelligence.

Portfolio de proyectos de datos construido como una progresión deliberada: cada proyecto suma una capa de dificultad técnica sobre el anterior, partiendo del análisis descriptivo y avanzando hacia lo predictivo, la nube y la automatización.

El hilo conductor es mi perfil de auditor: en todos los proyectos, antes de modelar o visualizar, audito la integridad de los datos y documento qué se excluye, cuánto y por qué. Estado declarado y evidencia no siempre coinciden — y eso se verifica, no se asume.

## 🧭 Ruta de aprendizaje y evolución técnica

| # | Proyecto | Foco | Salto técnico que incorpora | Estado |
|---|----------|------|------------------------------|--------|
| 1 | Ecommerce Customer Analytics | Análisis descriptivo + segmentación | SQL avanzado, RFM, K-Means no supervisado | ✅ Publicado |
| 2 | Dashboard Logístico (Tableau) | Business Intelligence | Pipeline reproducible Python→Tableau, data storytelling | ✅ Publicado |
| 3 | Auditoría Continua ISO 27001 | Ingeniería de datos + auditoría TI | PostgreSQL, SQL functions, trigger de inmutabilidad, pytest, Power BI | 🚧 Casi completo |
| 4 | Clasificador de Sentimiento (PNL) | Machine Learning supervisado | TF-IDF, regresión logística, análisis de errores profundo | 📋 Planificado |
| 5 | Monitor BOCBA | Sistema end-to-end en producción | Web scraping (Playwright), alertas, Docker, AWS, GitHub Actions, clasificación con LLM/embeddings (próximamente) | 📋 Planificado |

La ruta del portfolio avanza desde análisis descriptivo y visualización ejecutiva (P1-P2), hacia detección industrializada con trazabilidad de auditoría (P3), modelos predictivos/NLP (P4) y automatización aplicada a una fuente pública real (P5).

## 📂 Proyectos

### 1 · Ecommerce Customer Analytics ✅

Segmentación RFM y clustering K-Means sobre Online Retail II (1M+ transacciones, retail UK). Limpieza auditada en Python, persistencia en SQLite, métricas RFM con CTEs en SQL, análisis de cohortes y validación del modelo no supervisado contra reglas de negocio.

**Insight destacado:** el K-Means reveló 650 clientes "leales" que acumulan £3,1M históricos pero llevaban ~7 meses inactivos — un segmento de reactivación prioritario que las reglas tradicionales escondían.

`Python` · `Pandas` · `SQL (SQLite)` · `Scikit-Learn` · `Matplotlib/Seaborn`

## 2 · Dashboard Logístico — Tableau ✅

Dashboard interactivo en Tableau Public para analizar la cadena de entrega de Olist (~100.000 pedidos, 9 tablas). El proyecto utiliza un pipeline reproducible en Python/Pandas (`data_preparation.py`) que consolida los datos logísticos y genera la tabla final utilizada por Tableau.

Arquitectura de dos capas: **Python prepara los datos, Tableau los presenta**. El script de preparación, la documentación del pipeline y el dashboard quedan versionados juntos, asegurando trazabilidad entre transformación de datos e insights visuales.

**Insight destacado:** velocidad y confiabilidad logística no son lo mismo. El dashboard separa tiempos reales de entrega y cumplimiento de promesa para identificar problemas distintos según estado/región.

🔗 **[Ver dashboard en Tableau Public](https://public.tableau.com/app/profile/eduardo.govea/viz/DashboardLogsticoOlist/DashboardLogsticoOlistEntregasenBrasil2017-2018)**

**Python · Pandas · Tableau Public**

### 3 · Auditoría Continua ISO 27001 🚧 Casi completo

Sistema de auditoría continua sobre logs de acceso sintéticos, orientado a detectar posibles no conformidades vinculadas a controles de ISO 27001:2022. El proyecto combina generación de eventos, motor de detección en PostgreSQL, trazabilidad de hallazgos y validación automatizada con `pytest`.

El generador produce logs realistas con ruido operativo y casos ambiguos, no anomalías limpias. Sobre esos eventos se inyectan cuatro tipos de incumplimiento: acceso post-baja, horario anómalo, escalamiento de privilegios y violación de segregación de funciones. Cada anomalía queda mapeada a un control del Anexo A de ISO 27001:2022 (A.5.18, A.8.16, A.8.2, A.5.3).

El núcleo del proyecto es el criterio de auditoría aplicado a datos:

- **Motor SQL en PostgreSQL:** funciones de detección y orquestación para registrar hallazgos.
- **Tabla `findings`:** registro de hallazgos con severidad, evidencia, estado y trazabilidad.
- **Trigger de inmutabilidad:** una vez registrado, un hallazgo no puede modificarse ni eliminarse.
- **Mapeo anomalía → control ISO:** detección con sentido de cumplimiento, no solo análisis técnico de logs.
- **Tests automatizados:** validación del motor contra la verdad conocida generada por el generador, sin falsos positivos ni negativos sobre el ruido.

El proyecto se gestiona con un tablero Kanban en Jira, siguiendo un proceso deliberado: arquitectura → backlog → diseño → implementación → validación.

*Estado: motor SQL y tests finalizados; pendiente dashboard básico en Power BI y README técnico final.*

`Python` · `PostgreSQL` · `pytest` · `Power BI` · `Jira`

### 4 · Clasificador de Sentimiento — PNL 📋

Clasificación de ~100k reseñas reales de Olist (portugués) en positivas/negativas. El puntaje de estrellas provee las etiquetas → aprendizaje supervisado, complemento del K-Means no supervisado del P1.

El valor del proyecto no está en la métrica de accuracy, sino en el **análisis de errores profundo**: agrupar las fallas del modelo por patrón (sarcasmo, reseñas mixtas, portugués coloquial) y documentar *dónde y por qué* un modelo lineal no las captura. Opcionalmente, comparar contra un transformer (Hugging Face) para evidenciar el contraste.

`Python` · `Scikit-Learn` · `TF-IDF` · `Regresión Logística` · (opcional: `Hugging Face`)

### 5 · Monitor BOCBA 📋

Proyecto 100% original, nacido de un problema laboral real: un sistema que monitorea el Boletín Oficial de la Ciudad de Buenos Aires, identifica la normativa relevante y avisa automáticamente. Es la carta de ingeniería de sistemas del portfolio: vive en producción, corre solo y la infraestructura responde a una necesidad genuina.

- **Scraping con Playwright**, resolviendo el WAF de F5 BIG-IP (documentado como desafío técnico) + consumo de la API REST del Boletín.
- **Clasificación de relevancia:** filtrado de la normativa por relevancia. *Evolución prevista:* clasificación semántica mediante embeddings o LLMs para reemplazar las reglas basadas exclusivamente en keywords y generar un resumen de cada publicación relevante.
- **Alertas:** cuando aparece normativa relevante, llega un mail con el resumen generado, no solo el enlace.
- **AWS:** el monitor corre 24/7 desplegado en la nube (EC2 / Lambda + EventBridge).
- **GitHub Actions:** orquesta las corridas programadas y los tests.
- **Docker:** el sistema se contenedoriza para desplegarlo de forma reproducible en la nube.

`Python` · `Playwright` · `Docker` · `AWS` · `GitHub Actions` · `LLM / embeddings (previsto)`

## 🛠️ Stack general

**Lenguajes y datos:** Python, SQL (SQLite / PostgreSQL)
**Análisis y ML:** Pandas, NumPy, Scikit-Learn, LLM / embeddings (próximamente)
**Visualización / BI:** Tableau, Power BI, Matplotlib, Seaborn
**Ingeniería:** Docker, pytest, GitHub Actions, AWS
**Gestión:** Git, GitHub, Jira

## 👤 Autor

Eduardo Govea — Auditoría · Análisis de Datos · Machine Learning
🔗 LinkedIn · Tableau Public
