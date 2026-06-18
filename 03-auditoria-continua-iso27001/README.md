# 🔐 Auditoría Continua ISO 27001 — Motor de Detección sobre Logs de Acceso

Sistema de auditoría continua sobre logs de acceso sintéticos, orientado a detectar posibles no conformidades vinculadas a controles de ISO/IEC 27001:2022.

El proyecto combina generación de eventos, análisis en PostgreSQL, motor de detección SQL, registro de hallazgos con trazabilidad y validación automatizada con `pytest`.

---

## 🧭 Resumen ejecutivo

Este proyecto simula un escenario de auditoría continua sobre eventos de acceso. A partir de logs sintéticos generados con ruido operativo y casos ambiguos, el sistema detecta patrones compatibles con posibles incumplimientos de controles de seguridad de la información.

El foco no está en construir una infraestructura compleja, sino en demostrar criterio de auditoría aplicado a datos:

* detección de anomalías relevantes,
* trazabilidad entre evento, hallazgo y control ISO,
* preservación de la integridad de la evidencia,
* validación automatizada del motor de detección.

El MVP trabaja sobre PostgreSQL nativo. El archivo `docker-compose.yml` queda incluido como artefacto opcional de reproducibilidad, pero el desarrollo principal se realiza contra una base PostgreSQL local.

---

## 🎯 Objetivo

Construir un motor reproducible de auditoría continua que permita:

* generar logs de acceso sintéticos;
* inyectar casos de incumplimiento controlados;
* detectar anomalías mediante funciones SQL en PostgreSQL;
* registrar hallazgos con severidad, evidencia y trazabilidad;
* mapear cada anomalía a controles de ISO/IEC 27001:2022;
* validar el comportamiento del motor mediante tests automatizados.

---

## 🧱 Alcance del MVP

El MVP incluye:

* PostgreSQL nativo como base de análisis.
* Generador de logs sintéticos con ruido operativo y casos ambiguos.
* Motor de detección implementado en SQL.
* Funciones específicas por tipo de anomalía.
* Función orquestadora para ejecutar el análisis.
* Tabla `findings` para registrar hallazgos.
* Trigger de inmutabilidad sobre hallazgos.
* Clasificación por severidad.
* Mapeo anomalía → control ISO 27001:2022.
* Tests automatizados con `pytest`.
* Base preparada para dashboard ejecutivo/operativo en Power BI.

---

## 🚫 Fuera de alcance / diferido

Para mantener el proyecto cerrado, reproducible y defendible, se difieren algunos componentes:

* **Docker:** queda como artefacto opcional de reproducibilidad, pero el desarrollo principal se realiza contra PostgreSQL nativo.
* **Alertas por mail, GitHub Actions y AWS:** se trasladan al Proyecto 5, donde tienen mayor justificación por tratarse de monitoreo periódico.
* **Gap assessment desde Excel:** se separa como mini-proyecto independiente.

---

## 🛠️ Stack

* **Python** — generación de logs sintéticos y soporte de pruebas.
* **PostgreSQL** — almacenamiento, análisis y motor de detección.
* **SQL / PLpgSQL** — funciones de detección, orquestación y controles.
* **pytest** — validación automatizada del motor.
* **Power BI** — visualización ejecutiva/operativa pendiente.
* **Jira** — planificación y gestión del proyecto.

---

## 🧩 Tipos de anomalías detectadas

El motor trabaja sobre cuatro escenarios principales:

| Anomalía                              | Descripción                                                 | Control ISO 27001:2022 |
| ------------------------------------- | ----------------------------------------------------------- | ---------------------- |
| Acceso post-baja                      | Usuario con fecha de baja registra accesos posteriores      | A.5.18                 |
| Horario anómalo                       | Accesos fuera de horarios esperados                         | A.8.16                 |
| Escalamiento de privilegios           | Cambio o uso de privilegios elevados no esperado            | A.8.2                  |
| Violación de segregación de funciones | Usuario concentra acciones incompatibles dentro del proceso | A.5.3                  |

El objetivo no es detectar “eventos raros” sin contexto, sino transformar eventos técnicos en hallazgos con sentido de auditoría y cumplimiento.

---

## 🧱 Estructura del proyecto

```text
03-auditoria-continua-iso27001/
│
├── db/
│   └── scripts SQL, funciones, vistas y objetos de base de datos
│
├── generador/
│   └── generación de logs sintéticos y datos controlados
│
├── tests/
│   └── pruebas automatizadas del motor de detección
│
├── .env.example
├── .gitignore
├── docker-compose.yml
├── pytest.ini
├── requirements.txt
└── README.md
```

> El archivo `.env` no se versiona. Para configurar el entorno local, usar `.env.example` como plantilla.

---

## ⚙️ Flujo general del sistema

```text
Generador Python
        ↓
Logs sintéticos con ruido y casos ambiguos
        ↓
Carga en PostgreSQL
        ↓
Motor SQL de detección
        ↓
Tabla findings
        ↓
Severidad + evidencia + control ISO
        ↓
Tests automatizados / Power BI
```

---

## 🔍 Motor de detección

El motor en PostgreSQL analiza eventos de acceso y registra hallazgos en la tabla `findings`.

Cada hallazgo conserva:

* identificador del hallazgo;
* tipo de anomalía;
* usuario o entidad involucrada;
* control ISO asociado;
* severidad;
* evidencia;
* estado;
* fecha de detección.

La tabla de hallazgos cuenta con un trigger de inmutabilidad: una vez registrado, un hallazgo no puede modificarse ni eliminarse. Esto preserva la integridad de la evidencia generada por el proceso de auditoría.

---

## 🧪 Validación con pytest

El generador conserva una verdad conocida o `ground truth` de los casos inyectados. Los tests automatizados verifican que el motor detecte los casos esperados y controle falsos positivos sobre eventos de ruido.

La validación cubre:

* generación de datos;
* ejecución del motor de detección;
* existencia de hallazgos esperados;
* consistencia entre anomalía y control ISO;
* preservación de la integridad de hallazgos.

---

## 📊 Dashboard Power BI

El dashboard en Power BI queda previsto como cierre visual del proyecto.

Objetivo del dashboard:

* mostrar cantidad de hallazgos por severidad;
* distribuir hallazgos por tipo de anomalía;
* visualizar controles ISO más afectados;
* separar vista ejecutiva y vista operativa;
* facilitar lectura de riesgos y seguimiento.

Estado actual: pendiente de construcción final.

---

## ✅ Estado del proyecto

🚧 **Casi completo**

Estado actual:

* Motor SQL finalizado.
* Generador de logs implementado.
* Tabla `findings` y trigger de inmutabilidad implementados.
* Tests automatizados implementados.
* Pendiente dashboard básico en Power BI.
* Pendiente documentación técnica final.

---

## 🧾 Valor profesional del proyecto

Este proyecto demuestra:

* criterio de auditoría aplicado a datos;
* diseño de controles de integridad sobre evidencia;
* modelado de hallazgos con trazabilidad;
* uso de PostgreSQL como motor analítico y de control;
* validación automatizada de reglas de detección;
* documentación de alcance y exclusiones;
* transición desde análisis descriptivo hacia detección industrializada.

---

## 🚀 Ejecución local

### 1. Crear entorno virtual

```bash
python -m venv .venv
```

### 2. Activar entorno virtual

Windows:

```bash
.venv\Scripts\activate
```

Linux / Mac:

```bash
source .venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

Crear un archivo `.env` a partir de `.env.example` y completar los datos de conexión a PostgreSQL local.

### 5. Ejecutar tests

```bash
pytest
```

---

## 🔐 Nota sobre seguridad

El repositorio incluye `.env.example` como plantilla, pero no versiona credenciales reales. El archivo `.env` permanece local y está excluido por `.gitignore`.
