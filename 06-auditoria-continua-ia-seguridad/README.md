# 🛡️ Auditoría Continua de IA + Seguridad

📋 **Estado:** Planificado — documento de diseño inicial.

> **Continuación y evolución del Proyecto 3.** Toma el motor de auditoría continua del P3 —sobre la misma base de datos inventada (logs sintéticos con *ground truth*)— y lo lleva a **AI Assurance + seguridad**: el sistema deja de auditar solo controles y pasa a auditar también un **modelo de machine learning**, dentro de una envoltura de controles de ciberseguridad.

## 🎯 Objetivo

Demostrar, de forma acotada y reproducible, cómo se aplican controles de **Technology Risk & AI Assurance** sobre un sistema que incluye un componente de IA: auditar no solo los datos y los controles, sino también el propio modelo (su explicabilidad, su deriva, su sesgo) y la cadena de seguridad que lo rodea.

## 🧱 Capas incrementales

El proyecto se construye por capas, cada una funcional y defendible por separado.

### Capa 1 — Seguridad (DevSecOps)
- **SAST en CI** (bandit) y **escaneo de dependencias** (pip-audit).
- **Log de auditoría a prueba de manipulación** por encadenamiento de hashes, extendiendo el trigger de inmutabilidad del P3.
- Mapeo a ISO/IEC 27001:2022 — A.8.15, A.8.16, A.8.28.

### Capa 2 — Machine Learning
- **Detección de anomalías** sobre los logs de acceso sintéticos (Isolation Forest) como analítica de seguridad.

### Capa 3 — AI Assurance
- Auditoría del propio modelo: **explicabilidad (SHAP)**, linaje de datos, **monitoreo de drift**, chequeo de **sesgo/fairness** y **model card**.
- Mapeo a **ISO/IEC 42001** y **NIST AI RMF**.

## 🔗 Base

Se construye sobre el **Proyecto 3** (motor de detección, esquema de base y datos sintéticos), no desde cero. El P3 aporta la infraestructura de auditoría continua; el P6 le agrega el componente ML y la capa de assurance + seguridad.

## ⚠️ Alcance y límites

- Proyecto en etapa de diseño; la implementación se realizará por capas.
- Trabaja sobre **datos sintéticos**, no logs reales de una organización.
- No es una plataforma de AI governance productiva ni un SIEM.
- Cobertura **parcial** de los marcos (ISO 42001 / NIST AI RMF): se auditan riesgos seleccionados, no una conformidad completa.

## 🛠️ Stack previsto

`Python` · `PostgreSQL` · `pytest` · `bandit` · `pip-audit` · `Scikit-Learn` · `SHAP` · `Power BI` · *(marcos: ISO/IEC 42001 · NIST AI RMF)*
