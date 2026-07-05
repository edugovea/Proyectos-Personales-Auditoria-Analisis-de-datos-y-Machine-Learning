# Informe de resultados — Clasificador de sentimiento (Olist)

**Proyecto 4** · Continuación del Proyecto 2 sobre el dataset Olist
**Modelo base:** TF-IDF (unigramas y bigramas, `min_df=5`) + Regresión logística (`class_weight='balanced'`)
**Fecha:** julio 2026

---

## 1. Contexto y objetivo

Clasificar las reseñas de clientes de Olist (~100k reseñas en portugués brasileño) en
**positivas (4-5★)** y **negativas (1-2★)**, usando el puntaje de estrellas como etiqueta.
Las reseñas neutrales (3★) se descartan, y solo se usan las que tienen texto.

El objetivo de negocio no es maximizar el accuracy sino **detectar tempranamente los
comentarios críticos**: se prioriza el recall de la clase negativa.

## 2. Resultados del modelo base

| Métrica | Valor |
|---|---|
| Accuracy del baseline (siempre "positivo") | 0.709 |
| Accuracy del modelo | **0.93** |
| Recall clase negativa | **0.94** |
| Precision clase negativa | 0.83 |
| F1 clase negativa | 0.88 |
| Recall clase positiva | 0.92 |
| Precision clase positiva | 0.98 |

Matriz de confusión (test, n=7.484):

|  | Pred. negativo | Pred. positivo |
|---|---|---|
| **Real negativo** (2.178) | 2.058 | 120 |
| **Real positivo** (5.306) | 436 | 4.870 |

**Lectura:** el modelo supera al baseline por 22 puntos y captura el 94% de las reseñas
negativas — solo 120 quejas de 2.178 pasan desapercibidas. El costo es un 17% de "falsas
alarmas" en la clase negativa (436 reseñas positivas marcadas como negativas), un
trade-off aceptable cuando revisar una falsa alarma es más barato que perder un reclamo.

## 3. Análisis de errores

Total de errores en test: **556** (7,4% del conjunto).

- **Falsas alarmas** (real positivo / predicho negativo): 436 — **78%**
- **Quejas no detectadas** (real negativo / predicho positivo): 120 — **22%**

Se categorizó manualmente una muestra aleatoria de 30 errores (`random_state=42`):

| Patrón | Casos | % | Descripción |
|---|---|---|---|
| Reseña mixta / concesiva | 10 | 33% | Elogio + queja unidos por "mas", "porém", "apesar de", "só não dei nota máxima". El modelo lineal suma pesos de palabras positivas y negativas sin entender que la conjunción invierte o matiza lo que sigue. |
| Etiqueta ruidosa | 6 | 20% | El texto contradice al puntaje: "O produto ainda não chegou" con 4-5★, "o anel ficou apertado, como faço para trocar" con puntaje alto. El cliente puntúa su satisfacción global o al vendedor, no lo que escribió. |
| Queja logística separada del producto | 5 | 17% | El cliente distingue entre la tienda y el correo ("a empresa falida 'correios' falhou, prejudicando a loja e o cliente" — con puntaje alto). El modelo no puede separar a quién va dirigida la queja. |
| Negatividad implícita | 4 | 13% | Quejas sin vocabulario negativo fuerte ("Toalhas super finas", "não sei se voltarei a usar esse site") o con palabras fuera del vocabulario TF-IDF ("Descosturou logo que abri"). |
| Neutral / sin opinión todavía | 2 | 7% | "Recebi, porém ainda não testei". No hay sentimiento que clasificar. |
| Portugués coloquial / typos | 1 | 3% | "Olá BOM DIA Ñ recebir meus pididos" — las variantes ortográficas no existen en el vocabulario de entrenamiento. |
| Texto basura | 1 | 3% | "FBFHJJKLI\ZXDAd" — inclasificable para cualquier modelo. |
| Error genuino sin patrón | 1 | 3% | Reseña claramente positiva mal clasificada, probablemente por negaciones ("não fica com gosto"). |

### 3.1 Hallazgo principal: la etiqueta es la fuente de ruido más subestimada

Sumando etiquetas ruidosas, neutrales y texto basura, **~30-40% de los "errores" del
modelo no son errores de modelado sino límites del dato**: la etiqueta (estrellas)
mide la satisfacción global de la transacción, mientras el texto puede referirse solo
a un aspecto (el envío, el vendedor, una parte faltante). En varios casos el modelo
leyó el texto *mejor que la etiqueta*.

Implicancia de auditoría: cualquier métrica reportada sobre este dataset tiene un piso
de error irreducible por ruido de etiquetado. Un accuracy de 100% no solo es imposible:
sería sospechoso.

### 3.2 Límite estructural del modelo lineal

El patrón dominante (reseñas mixtas, 33%) es exactamente el caso donde un modelo de
bolsa de palabras no puede mejorar: entender que "chegou no prazo, **porém** veio
faltando peças" es negativo requiere procesar el orden y la estructura de la frase,
no solo qué palabras contiene. Este es el argumento empírico para comparar contra un
transformer (BERTimbau), que sí modela contexto.

## 4. Limitaciones y sesgos

- **Etiquetado por estrellas:** proxy imperfecto del sentimiento del texto (ver 3.1).
- **Descarte de 3★:** simplifica el problema binario pero elimina justo los casos
  ambiguos; el modelo no está preparado para reseñas tibias.
- **Solo reseñas con texto:** la mayoría de las reseñas de Olist no tienen comentario;
  los resultados no generalizan al total de órdenes.
- **Dominio temporal y de plataforma:** e-commerce brasileño 2016-2018; el vocabulario
  y los patrones de queja pueden no transferirse a otros dominios.

## 5. Próximos pasos

1. Comparar contra un transformer pre-entrenado en portugués (**BERTimbau**) sobre los
   mismos 556 errores, para cuantificar cuántas reseñas mixtas resuelve el contexto.
2. Evaluar un etiquetado alternativo para medir el ruido (p. ej. re-etiquetar a mano
   una muestra y medir la concordancia texto-estrellas).
3. Documentar las conclusiones finales en el README del proyecto.
