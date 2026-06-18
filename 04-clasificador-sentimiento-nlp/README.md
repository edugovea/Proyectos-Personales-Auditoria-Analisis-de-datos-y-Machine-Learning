# 04 - Clasificador de Sentimiento con NLP

📋 **Estado:** Planificado / En desarrollo

## Objetivo

Construir un modelo de clasificación de sentimiento aplicado a reseñas de clientes, utilizando técnicas de procesamiento de lenguaje natural y machine learning supervisado.

El proyecto busca analizar texto no estructurado para identificar tempranamente fricciones en la experiencia del usuario, clasificar opiniones positivas y negativas, detectar patrones de disconformidad y automatizar la categorización inicial de comentarios o reclamos.

## Valor analítico

Este proyecto busca demostrar cómo las técnicas de NLP pueden transformar texto libre en información estructurada para apoyar decisiones de negocio, priorización de reclamos, monitoreo de satisfacción y detección temprana de riesgos operativos o reputacionales.

Desde un enfoque auditor, el proyecto no solo se centra en entrenar un modelo, sino también en documentar criterios de clasificación, calidad del dataset, limitaciones, sesgos y métricas de evaluación.

## Enfoque previsto

* Limpieza y normalización de texto.
* Análisis exploratorio de reseñas.
* Definición de etiquetas de sentimiento.
* Tokenización y vectorización con TF-IDF.
* Entrenamiento de modelos supervisados de clasificación.
* Evaluación con matriz de confusión, precision, recall y F1-score.
* Análisis de errores y revisión de casos mal clasificados.
* Documentación de limitaciones, sesgos del dataset y criterios de clasificación.

## Stack previsto

* Python
* Pandas
* NumPy
* Scikit-learn
* NLP
* TF-IDF
* Matplotlib / Seaborn
* Jupyter Notebook

## Estructura prevista del proyecto

```text
04-clasificador-sentimiento-nlp/
│
├── data/
│   ├── raw/
│   └── processed/
│
├── notebooks/
│   └── 01_eda_modelo_base.ipynb
│
├── reports/
│   └── informe_resultados.md
│
├── src/
│   ├── preprocessing.py
│   ├── train_model.py
│   └── evaluate_model.py
│
├── README.md
└── requirements.txt
```

## Métricas previstas

El modelo será evaluado utilizando métricas orientadas a clasificación supervisada:

* Accuracy
* Precision
* Recall
* F1-score
* Matriz de confusión

La evaluación priorizará no solo el rendimiento general, sino también la capacidad del modelo para identificar correctamente comentarios negativos o potencialmente críticos.

## Próximos pasos

* Seleccionar dataset.
* Preparar notebook de análisis exploratorio.
* Definir criterios de etiquetado.
* Entrenar modelo base.
* Evaluar métricas de clasificación.
* Documentar resultados y limitaciones.
* Publicar conclusiones finales del proyecto.

## Estado del repositorio

Este proyecto forma parte de un portfolio personal de auditoría, análisis de datos y machine learning. Actualmente se encuentra en etapa de planificación y diseño.
