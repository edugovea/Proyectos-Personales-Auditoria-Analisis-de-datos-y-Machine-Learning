"""
Buscar por NUMERO de Boletin (BOCBA)
====================================
La API oficial solo consulta por fecha, pero este script resuelve a que fecha
corresponde el numero pedido (ver resolver_fecha_boletin en el monitor) y
despues reutiliza toda la maquinaria de monitor_bocba_v2.py.

Doble funcion:
  1. Sin palabra -> analiza el boletin completo con las keywords, siglas y
     sinonimos del monitor (mismo criterio de relevancia por materia).
  2. Con palabra -> busca SOLO esa palabra o frase en ese boletin.

Aprovecha el cache: si ese boletin ya fue procesado alguna vez, los PDFs no
se vuelven a descargar y la busqueda es casi instantanea.

Uso (desde la terminal, parado en esta carpeta):
  py buscar_bocba.py 7394                  -> analiza el Boletin N 7394 completo
  py buscar_bocba.py 7394 designacion      -> busca "designacion" en el N 7394
  py buscar_bocba.py 7394 "obra publica"   -> una frase (va entre comillas)
"""

import json
import sys
from datetime import datetime

import requests
import monitor_bocba_v2 as m   # <- reutiliza las funciones que ya funcionan

# Cuantos documentos mostrar en consola (el detalle completo va al PDF/app).
MOSTRAR_CONSOLA = 15


def keywords_del_monitor():
    """La misma lista que arma main() del monitor: keywords + siglas + sinonimos."""
    kws = [(k, m.norm(k), False) for k in m.KEYWORDS]
    kws += [(s, m.norm(s), True) for s in m.SIGLAS]
    for concepto, variantes in m.SINONIMOS.items():
        for v in variantes:
            kws.append((concepto, m.norm(v), False))
    return kws


def main():
    if len(sys.argv) < 2 or not sys.argv[1].isdigit():
        print(__doc__)
        return
    numero = int(sys.argv[1])
    palabra = sys.argv[2] if len(sys.argv) > 2 else None

    m.CARPETA.mkdir(exist_ok=True)
    m.CACHE_PDF.mkdir(parents=True, exist_ok=True)
    session = requests.Session()

    print(f"Resolviendo la fecha del Boletin N {numero}...")
    fecha = m.resolver_fecha_boletin(session, numero)
    if fecha is None:
        print(f"No se pudo encontrar el Boletin N {numero}. "
              "Revisa el numero (o la API no lo tiene disponible).")
        return
    print(f"Boletin N {numero} -> publicado el {fecha.strftime('%d/%m/%Y')}\n")

    if palabra:
        keywords = [(palabra, m.norm(palabra), False)]
        print(f"Buscando '{palabra}' en el Boletin N {numero}...\n")
    else:
        keywords = keywords_del_monitor()
        print(f"Analizando el Boletin N {numero} con el criterio del monitor...\n")

    res = m.procesar_dia(session, fecha.strftime("%d-%m-%Y"), keywords)

    hall = res.get("hallazgos", [])
    print("\n" + "=" * 60)
    if not hall:
        objetivo = f"'{palabra}'" if palabra else "las keywords del monitor"
        print(f"Sin coincidencias de {objetivo} en el Boletin N {numero}.")
        print("=" * 60)
        return

    orden = {"ALTA": 0, "MEDIA": 1, "BAJA": 2}
    hall = sorted(hall, key=lambda d: (orden.get(d.get("relevancia", "BAJA"), 3),
                                       -d.get("score", 0)))
    conteo = {"ALTA": 0, "MEDIA": 0, "BAJA": 0}
    for d in hall:
        conteo[d.get("relevancia", "BAJA")] += 1
    print(f"Boletin N {numero} ({fecha.strftime('%d/%m/%Y')}): "
          f"{len(hall)} documento(s) con coincidencias "
          f"({conteo['ALTA']} ALTA, {conteo['MEDIA']} MEDIA, "
          f"{conteo['BAJA']} BAJA)\n")

    # En consola solo lo mas relevante; el detalle completo va al PDF y la app.
    for d in hall[:MOSTRAR_CONSOLA]:
        rel = d.get("relevancia", "BAJA")
        titulo = d.get("cita") or f"Doc {d['doc_id']}"
        etiquetas = ", ".join(d.get("keywords", {}).keys())
        print(f"  [{rel}] {titulo}")
        print(f"      Etiquetas: {etiquetas}")
        print(f"      {d.get('url', '')}")
        for b in d.get("keywords", {}).values():
            ejemplo = b.get("cuerpo") or b.get("anexo")
            if ejemplo:
                print(f"      Ej: {ejemplo[0]['ctx'][:160]}")
                break
    if len(hall) > MOSTRAR_CONSOLA:
        print(f"\n  ... y {len(hall) - MOSTRAR_CONSOLA} documento(s) mas "
              f"(detalle completo en la gacetilla PDF y en la app).")

    print()
    informe = {"ejecucion": datetime.now().isoformat(),
               "etiquetas": ([palabra] if palabra else m.KEYWORDS),
               "siglas": ([] if palabra else m.SIGLAS),
               "dias": [res]}

    # Analisis completo -> se guarda como reporte para que la APP lo muestre
    # (con palabra libre no, para no ensuciar las etiquetas del tablero).
    if not palabra:
        salida = m.CARPETA / f"reporte_{fecha.strftime('%d-%m-%Y')}.json"
        salida.write_text(json.dumps(informe, ensure_ascii=False, indent=2),
                          encoding="utf-8")
        print(f"Reporte guardado: {salida}")
        print("  -> Abri la app y toca 'Actualizar datos' para explorarlo "
              "con filtros y tabla.")

    sufijo = f"_{m._slug(palabra, 30)}" if palabra else ""
    ruta_pdf = m.CARPETA / f"gacetilla_boletin_{numero}{sufijo}.pdf"
    try:
        generada = m.generar_pdf_gacetilla(informe, ruta_pdf)
    except PermissionError:
        print(f"AVISO: no se pudo escribir {ruta_pdf.name} porque esta "
              f"abierto en el visor de PDF. Cerralo y volve a correr.")
        generada = None
    if generada:
        print(f"Gacetilla PDF: {ruta_pdf}")
        # Abrirla automaticamente con el visor por defecto (solo Windows;
        # si falla no importa, el archivo queda igual).
        try:
            import os
            os.startfile(ruta_pdf)
        except Exception:
            pass
    print("=" * 60)


if __name__ == "__main__":
    main()
