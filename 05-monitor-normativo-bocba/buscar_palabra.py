"""
Buscar UNA sola palabra en el boletin de HOY
============================================
Reutiliza toda la maquinaria de monitor_bocba_v2.py (descarga de PDFs, cache y
busqueda), pero en vez de la lista completa de KEYWORDS busca una unica palabra
o frase. No modifica el monitor original: solo lo "importa" y usa sus funciones.

Aprovecha el cache: si hoy ya corriste el monitor v2, los PDFs ya estan bajados,
asi que esta busqueda es casi instantanea.

Uso (desde la terminal, parado en esta carpeta):
  py buscar_palabra.py                 -> busca la PALABRA de abajo en el boletin de hoy
  py buscar_palabra.py designacion     -> busca "designacion"
  py buscar_palabra.py "obra publica"  -> una frase (va entre comillas)
  py buscar_palabra.py designacion 12-06-2026   -> palabra + fecha puntual
"""

import sys
from datetime import date

import requests
import monitor_bocba_v2 as m   # <- reutiliza las funciones que ya funcionan

# ----------------------------------------------------------------------
# Palabra/frase a buscar. Cambiala aca, o pasala como argumento al correr.
# ----------------------------------------------------------------------
PALABRA = "designación"


def main():
    # Argumentos: [palabra] [fecha opcional dd-mm-yyyy]
    palabra = sys.argv[1] if len(sys.argv) > 1 else PALABRA
    if len(sys.argv) > 2:
        fecha = sys.argv[2].replace("/", "-")
    else:
        fecha = date.today().strftime("%d-%m-%Y")

    m.CARPETA.mkdir(exist_ok=True)
    m.CACHE_PDF.mkdir(parents=True, exist_ok=True)
    session = requests.Session()

    # Una sola "keyword", tratada como termino normal (acepta plurales/variantes,
    # ej: designacion -> designaciones). El False = "no es sigla exacta".
    keywords_norm = [(palabra, m.norm(palabra), False)]

    print(f"Buscando '{palabra}' en el boletin ({fecha.replace('-', '/')})...\n")

    # Esto hace TODO: baja el boletin, los PDFs y busca la palabra.
    res = m.procesar_dia(session, fecha, keywords_norm)

    hall = res.get("hallazgos", [])
    print("\n" + "=" * 60)
    if not hall:
        print(f"Sin coincidencias de '{palabra}' en el boletin de la fecha.")
    else:
        # Ordenar por relevancia (Alta primero)
        orden = {"ALTA": 0, "MEDIA": 1, "BAJA": 2}
        hall = sorted(hall, key=lambda d: (orden.get(d.get("relevancia", "BAJA"), 3),
                                           -d.get("score", 0)))
        print(f"'{palabra}': {len(hall)} documento(s) donde aparece:\n")
        for d in hall:
            kw = d["keywords"].get(palabra, {"cuerpo": [], "anexo": []})
            # paginas donde aparece, separadas por fuente
            pags_cuerpo = sorted({h["pagina"] for h in kw["cuerpo"]})
            pags_anexo = sorted({h["pagina"] for h in kw["anexo"]})
            donde = []
            if pags_cuerpo:
                donde.append(f"cuerpo p.{','.join(map(str, pags_cuerpo))}")
            if pags_anexo:
                donde.append(f"anexo p.{','.join(map(str, pags_anexo))}")
            rel = d.get("relevancia", "BAJA")
            titulo = d.get("cita") or f"Doc {d['doc_id']}"
            print(f"  [{rel}] {titulo}   [{'; '.join(donde)}]")
            print(f"      {d['url']}")
            ejemplo = kw["cuerpo"] or kw["anexo"]
            if ejemplo:
                print(f"      Ej: {ejemplo[0]['ctx'][:160]}")
    print("=" * 60)


if __name__ == "__main__":
    main()
