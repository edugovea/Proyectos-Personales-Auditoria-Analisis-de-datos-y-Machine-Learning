# Informe de resultados — Clasificador de sentimiento (Olist)

**Proyecto 4** · Continuación del Proyecto 2 sobre el dataset Olist
**Modelo base:** TF-IDF (unigramas y bigramas, `min_df=5`) + Regresión logística (`class_weight='balanced'`)
**Modelo de comparación:** BERTimbau base (`neuralmind/bert-base-portuguese-cased`) con fine-tuning de 2 épocas
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

## 4. Comparación contra un transformer: BERTimbau

Para cuantificar el límite estructural del modelo lineal (sección 3.2), se realizó
fine-tuning de **BERTimbau** — un BERT pre-entrenado en portugués brasileño — sobre el
mismo split de entrenamiento (mismo `random_state`, comparación directa sobre el mismo
conjunto de test).

| Métrica | Lineal (TF-IDF + RL) | BERTimbau | Diferencia |
|---|---|---|---|
| Accuracy | 0.93 | **0.95** | +2 pts |
| F1 macro | 0.91 | **0.94** | +3 pts |
| Precision negativo | 0.83 | **0.91** | +8 pts |
| **Recall negativo** | **0.94** | 0.92 | **-2 pts** |
| Errores totales en test | 556 | 366 | -34% |

### 4.1 Qué resuelve el contexto (y qué no)

Sobre los 556 errores del modelo lineal:

- **BERTimbau resuelve 298 (54%)** — concentrados en las reseñas mixtas/concesivas,
  donde entender que "porém" invierte lo que sigue requiere procesar la estructura de
  la frase, no solo contar palabras.
- **258 errores (46%) persisten en ambos modelos.** Al revisarlos, dominan las
  categorías de *etiqueta ruidosa* y *texto no informativo*: "Recebi a máscara com
  trincas, como faço para reclamar?" con puntaje alto, "Sem comentários" etiquetado
  positivo, texto basura. Ninguna arquitectura puede corregir un dato donde el texto y
  la etiqueta se contradicen — este es el **piso de ruido irreducible** del dataset,
  ahora medido empíricamente (~3,4% del test).

### 4.2 El "mejor" modelo depende de la métrica de negocio

Un matiz central para la decisión: en la métrica que este proyecto prioriza — el
**recall de la clase negativa** (no perderse quejas) — el modelo lineal es levemente
superior (0.94 vs 0.92). BERTimbau gana en todo lo demás, especialmente en reducir
falsas alarmas (+8 pts de precision negativa).

A eso se suma el costo operativo: la regresión logística entrena en segundos en CPU;
BERTimbau requirió ~20 minutos en GPU (T4) y su inferencia es órdenes de magnitud más
lenta. Para un tablero de alertas de reclamos donde el recall negativo manda y el
volumen es alto, el modelo lineal es defendible; para clasificación de propósito
general con menos falsas alarmas, el transformer justifica su costo.

## 5. Limitaciones y sesgos

- **Etiquetado por estrellas:** proxy imperfecto del sentimiento del texto (ver 3.1).
- **Descarte de 3★:** simplifica el problema binario pero elimina justo los casos
  ambiguos; el modelo no está preparado para reseñas tibias.
- **Solo reseñas con texto:** la mayoría de las reseñas de Olist no tienen comentario;
  los resultados no generalizan al total de órdenes.
- **Dominio temporal y de plataforma:** e-commerce brasileño 2016-2018; el vocabulario
  y los patrones de queja pueden no transferirse a otros dominios.
- **Longitud truncada:** los comentarios están limitados a ~208 caracteres por la
  plataforma, lo que favorece reseñas telegráficas y ambiguas.

## 6. Conclusiones

1. El modelo base supera ampliamente al baseline (0.93 vs 0.71) y cumple el objetivo
   de negocio: detecta el 94% de las reseñas negativas.
2. El análisis manual de errores revela que **una parte sustancial de los "errores" es
   ruido de etiquetado**, no falla de modelado: las estrellas miden satisfacción global,
   el texto puede referirse a un solo aspecto.
3. La comparación con BERTimbau valida ambas hipótesis: el contexto resuelve el 54% de
   los errores (las reseñas mixtas), y el 46% restante — dominado por etiquetas
   ruidosas — persiste en cualquier arquitectura.
4. La elección de modelo depende de la métrica de negocio: para maximizar detección de
   quejas a bajo costo, el lineal es defendible; para minimizar falsas alarmas, el
   transformer justifica su costo computacional.

**Extensión posible:** re-etiquetar a mano una muestra para medir la concordancia
texto-estrellas y estimar con precisión la tasa de ruido de etiquetado.
