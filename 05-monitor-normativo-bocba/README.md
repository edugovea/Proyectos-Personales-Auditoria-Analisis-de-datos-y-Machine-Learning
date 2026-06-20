# 🔎 05 - Monitor Normativo BOCBA

🚧 **Estado:** ~50% desarrollado — versión demo, próximamente a subir

## Objetivo

Desarrollar una herramienta experimental para facilitar la búsqueda, filtrado y seguimiento de normativa publicada en el Boletín Oficial de la Ciudad de Buenos Aires, utilizando fuentes públicas.

El proyecto está orientado a explorar cómo la automatización, el procesamiento documental y la organización de información normativa pueden apoyar tareas de auditoría, control interno, cumplimiento normativo y monitoreo de información pública.

## Valor analítico

La herramienta busca reducir tiempos de búsqueda normativa, mejorar la trazabilidad de publicaciones relevantes y generar insumos estructurados para análisis de auditoría, cumplimiento y seguimiento de cambios regulatorios.

Desde un enfoque de auditoría, el proyecto apunta a convertir publicaciones normativas dispersas en información consultable, filtrable y documentada.

## Enfoque previsto

* Consulta de publicaciones del Boletín Oficial a partir de fuentes públicas.
* Descarga y procesamiento de documentos publicados.
* Extracción de texto desde PDFs.
* Búsqueda por palabras clave.
* Filtros por fecha, organismo, tema o tipo de norma.
* Organización de resultados relevantes.
* Persistencia de resultados para seguimiento histórico.
* Exportación de información para análisis posterior.
* Posible generación de alertas o reportes.

## Stack técnico

### Tecnologías utilizadas / probadas

* Python
* Pandas
* Requests
* BeautifulSoup
* pdfplumber
* PyPDF2
* SQLite
* PostgreSQL
* Git / GitHub

### Evolución prevista

* Docker / Docker Compose para facilitar la ejecución reproducible del proyecto.
* Automatización periódica de consultas.
* Alertas por palabras clave.
* Exportación de resultados a CSV, Excel o PDF.
* Evaluación de Selenium solo si alguna fuente pública requiere navegación dinámica.

## Enfoque técnico previsto

La herramienta está pensada para consultar fuentes públicas, descargar o procesar documentos normativos, extraer texto desde PDFs, aplicar filtros por palabras clave y almacenar resultados relevantes en una base de datos para seguimiento histórico.

En una primera versión demo, el almacenamiento puede resolverse con SQLite. Como evolución, se contempla PostgreSQL y Docker para una arquitectura más robusta, reproducible y escalable.

## Estructura prevista del proyecto

```text
05-monitor-bocba/
│
├── data/
│   ├── raw/
│   └── processed/
│
├── notebooks/
│   └── 01_exploracion_fuente_publica.ipynb
│
├── src/
│   ├── downloader.py
│   ├── pdf_extractor.py
│   ├── keyword_search.py
│   ├── database.py
│   └── export_results.py
│
├── reports/
│   └── ejemplos_busqueda.md
│
├── README.md
└── requirements.txt
```

## Posibles casos de uso

* Búsqueda rápida de normativa por palabras clave.
* Seguimiento de publicaciones vinculadas a organismos específicos.
* Identificación de normas relacionadas con auditoría, control interno, datos personales, tecnología o cumplimiento.
* Organización de resultados para análisis posterior.
* Generación de insumos para reportes o tableros.

## Aviso

Este proyecto es personal, educativo y demostrativo. No representa una herramienta oficial del Gobierno de la Ciudad de Buenos Aires ni contiene información interna, reservada o confidencial.

Toda la información utilizada proviene de fuentes públicas.

## Próximos pasos

* Publicar versión demo sanitizada.
* Documentar flujo de búsqueda.
* Agregar ejemplos con datos públicos.
* Incorporar capturas y casos de uso.
* Implementar persistencia inicial en SQLite.
* Evaluar evolución a PostgreSQL.
* Incorporar Docker para facilitar la ejecución del entorno.
* Analizar posible incorporación de alertas por palabras clave.

## Estado del repositorio

Este proyecto forma parte de un portfolio personal de auditoría, análisis de datos, automatización y cumplimiento normativo. Actualmente se encuentra en etapa de desarrollo de una versión demo pública.

