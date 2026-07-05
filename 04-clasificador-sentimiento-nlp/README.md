# 💬 Clasificador de Sentimiento con NLP

🚧 **Estado:** En desarrollo

> **Continuación del Proyecto 2.** Sobre el mismo dataset **Olist**, este proyecto da el salto de la visualización descriptiva (BI) al modelado predictivo: del *qué pasó* al *qué dice el cliente*.

## Objetivo

Construir un modelo de clasificación de sentimiento sobre las **reseñas de clientes de Olist** (~100k reseñas en portugués), clasificándolas en positivas y negativas mediante técnicas de procesamiento de lenguaje natural y machine learning supervisado.

El puntaje de estrellas de cada reseña provee la etiqueta (aprendizaje supervisado). El proyecto busca analizar texto no estructurado para identificar tempranamente fricciones en la experiencia del usuario, clasificar opiniones, detectar patrones de disconformidad y automatizar la categorización inicial de comentarios.

## Valor analítico

El proyecto busca demostrar cómo las técnicas de NLP pueden transformar texto libre en información estructurada para apoyar decisiones de negocio, priorización de reclamos, monitoreo de satisfacción y detección temprana de riesgos operativos o reputacionales.

Desde un enfoque de auditor, el foco no está solo en entrenar un modelo ni en maximizar el accuracy, sino en el **análisis de errores profundo**: agrupar las fallas del modelo por patrón (sarcasmo, reseñas mixtas, portugués coloquial) y documentar *dónde y por qué* un modelo lineal no las captura. También se documentan criterios de clasificación, calidad del dataset, limitaciones y sesgos.

## Enfoque previsto

* Limpieza y normalización de texto (portugués).
* Análisis exploratorio de las reseñas de Olist.
* Definición de etiquetas de sentimiento a partir del puntaje de estrellas.
* Tokenización y vectorización con TF-IDF.
* Entrenamiento de modelos supervisados de clasificación (regresión logística como base).
* Evaluación con matriz de confusión, precision, recall y F1-score.
* Análisis de errores y revisión de casos mal clasificados.
* Documentación de limitaciones, sesgos del dataset y criterios de clasificación.
* *(Opcional)* Comparación contra un transformer (Hugging Face) para evidenciar el contraste con el modelo lineal.

## Stack previsto

* Python
* Pandas
* NumPy
* Scikit-learn
* TF-IDF
* Matplotlib / Seaborn
* Jupyter Notebook
* *(opcional: Hugging Face)*

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

El modelo será evaluado con métricas orientadas a clasificación supervisada:

* Accuracy
* Precision
* Recall
* F1-score
* Matriz de confusión

La evaluación priorizará no solo el rendimiento general, sino también la capacidad del modelo para identificar correctamente comentarios negativos o potencialmente críticos.

## Próximos pasos

* Obtener y cargar el dataset de reseñas de Olist.
* Preparar el notebook de análisis exploratorio.
* Definir criterios de etiquetado a partir del puntaje de estrellas.
* Entrenar el modelo base.
* Evaluar métricas de clasificación.
* Documentar resultados, errores y limitaciones.
* Publicar conclusiones finales del proyecto.

## Estado del repositorio

Este proyecto forma parte de un portfolio personal de auditoría, análisis de datos y machine learning. Actualmente se encuentra en etapa de planificación y diseño, como continuación del Proyecto 2 sobre el dataset Olist.
