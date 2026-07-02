"""
Monitor BOCBA v2 - Vigilancia del Boletin Oficial de la CABA (enfoque PDF directo)
==================================================================================
A diferencia de la v1, NO usa el buscador normativo (/normativaba), que tiene
retraso de indexacion y a veces tira 500. En cambio:

  1. Pide el boletin del dia via API REST oficial (api-restboletinoficial)
  2. Enumera TODOS los documentos publicados ese dia
  3. Descarga cada documento (/download/{id}) y extrae su texto con fitz
  4. Busca las keywords en el texto (deterministico, con contexto y nro de pagina)
  5. Genera reporte JSON + resumen en consola + PDF ejecutivo + Gacetilla

Esto detecta lo que realmente salio en el boletin, sin depender de ningun indice.

Requisitos:
  py -m pip install requests pymupdf reportlab

Uso:
  py monitor_bocba_v2.py                          # boletin de hoy
  py monitor_bocba_v2.py 16-06-2026               # fecha puntual (dd-mm-yyyy)
  py monitor_bocba_v2.py 08-06-2026 12-06-2026    # rango de fechas (inclusive)
"""

import sys
import re
import json
import time
import unicodedata
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from pathlib import Path

import requests

# Consola en UTF-8: que las tildes y enies se vean bien en Windows.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Falta PyMuPDF. Instalalo con:  py -m pip install pymupdf")
    sys.exit(1)

# reportlab es opcional: si no esta, el script funciona igual pero sin PDF.
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle)
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False

# ----------------------------------------------------------------------
# CONFIGURACION
# ----------------------------------------------------------------------

KEYWORDS = [
    "Analisis y Datos",
    "digitalizacion",
    "datos personales",
    "ciberseguridad",
    "inteligencia artificial",
    "sistema informatico",
    "seguridad informatica",
    "Sindicatura General",
    "auditoria",
    # Temas pedidos por el area legal (gacetilla semanal SGCBA)
    "control interno",
    "acceso a la informacion",
    "transparencia activa",
    "mesa de entradas",
]

# Siglas: coincidencia EXACTA, sin sufijos.
SIGLAS = [
    "DGAYD",
    "SGCBA",
    "OFIP",
    "DGAIGA",
]

# Sinonimos / terminos relacionados. Cada CONCEPTO (la clave, que es como se
# muestra en los reportes) agrupa todas sus variantes. Al buscar cualquiera de
# las variantes, el hallazgo se reporta bajo el nombre del concepto.
# Editable: agrega o saca conceptos y variantes segun lo que necesites vigilar.
# Nota: la busqueda ignora acentos y, salvo siglas, admite sufijos (designa ->
# designar, designacion, designase...). Por eso conviene usar la raiz corta.
SINONIMOS = {
    "Designacion de personal": [
        "designa", "design", "nombramiento", "nombrar",
        "asignar funciones", "cubrir el cargo", "cubrir cargo",
    ],
    "Renuncia / Cese": [
        "acepta la renuncia", "renuncia", "cesar", "cese",
        "limitar los servicios", "dejar sin efecto la designacion",
    ],
    "Contratacion": [
        "contratacion", "licitacion", "adjudica", "locacion de servicios",
        "compra directa", "orden de compra",
    ],
    # Conceptos pedidos por el area legal (gacetilla semanal SGCBA)
    "Cambio de estructura": [
        "estructura organizativa", "estructura organica",
        "misiones y funciones", "modifica la estructura",
    ],
    "Informe Final de Gestion": [
        "informe final de gestion",
    ],
    "Ley de Modernizacion": [
        "ley 3.304", "ley n 3.304", "ley de modernizacion",
    ],
}

# ----------------------------------------------------------------------
# MATRIZ DE RIESGO POR MATERIA (criterio de auditoria + pedido del area legal)
# ----------------------------------------------------------------------
# El TEMA define el piso del que "nace" cada norma; los agravantes del score
# pueden subirla UN nivel, pero el volumen de menciones nunca fabrica una
# ALTA desde un tramite de rutina. Editable: mover materias entre pisos.
PISOS = {
    "ALTA": [
        # Riesgo legal / control interno: una mencion ya amerita revision
        "datos personales", "ciberseguridad", "seguridad informatica",
        "Sindicatura General", "SGCBA", "auditoria", "DGAYD",
        "control interno", "OFIP", "acceso a la informacion",
        "transparencia activa", "DGAIGA",
        # Items que el area legal incluye SIEMPRE en su gacetilla
        "Informe Final de Gestion", "Cambio de estructura",
    ],
    "MEDIA": [
        "inteligencia artificial", "sistema informatico", "digitalizacion",
        "Analisis y Datos", "mesa de entradas", "Contratacion",
        "Ley de Modernizacion",
    ],
    "BAJA": [
        # Rutina administrativa: solo relevante con agravantes o cargo alto
        "Designacion de personal", "Renuncia / Cese",
    ],
}

API = "https://api-restboletinoficial.buenosaires.gob.ar"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/126.0.0.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
}

CARPETA = Path("reportes_bocba")
CACHE_PDF = CARPETA / "cache_pdf"
NORMATIVAS = CARPETA / "normativas"   # PDFs de las normas que matchean
TIMEOUT = 60
CONTEXTO_CHARS = 120
INCLUIR_ANEXOS = True
INCLUIR_VARIANTES = True
MAX_WORKERS = 8       # descargas en paralelo (subir/bajar segun tu conexion)
REINTENTOS = 2        # reintentos ante errores 5xx / red intermitente
GUARDAR_NORMATIVAS = True   # descargar el PDF de cada norma que matchee


# ----------------------------------------------------------------------
# UTILIDADES
# ----------------------------------------------------------------------

def norm(s: str) -> str:
    """Sin acentos, minusculas."""
    return (unicodedata.normalize("NFKD", s)
            .encode("ascii", "ignore").decode().lower())


# Materia (normalizada) -> piso. Se arma aca porque necesita norm().
PISO_MATERIA = {norm(m): nivel for nivel, ms in PISOS.items() for m in ms}

# Reglas especiales del area legal (se evaluan sobre el sumario/cita):
#  - Designaciones y renuncias importan de Director General "para arriba"
#    (DG, subsecretarios, secretarios, ministros, autoridades fuera de nivel).
RE_ACTO_PERSONAL = re.compile(r"\b(design|renunci|cesa|cese)")
RE_CARGO_ALTO = re.compile(
    r"\b(director\w* general\w*|subsecretari\w+|secretari[oa]s?\b"
    r"|ministr\w+|fuera de nivel)")


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def rango_fechas() -> list:
    args = [a.replace("/", "-") for a in sys.argv[1:]]
    if not args:
        return [date.today().strftime("%d-%m-%Y")]
    if len(args) == 1:
        return [args[0]]
    desde = datetime.strptime(args[0], "%d-%m-%Y").date()
    hasta = datetime.strptime(args[1], "%d-%m-%Y").date()
    if hasta < desde:
        desde, hasta = hasta, desde
    fechas = []
    actual = desde
    while actual <= hasta:
        fechas.append(actual.strftime("%d-%m-%Y"))
        actual = date.fromordinal(actual.toordinal() + 1)
    return fechas


# ----------------------------------------------------------------------
# API REST
# ----------------------------------------------------------------------

# Una Session por hilo: requests.Session no es 100% thread-safe para compartir.
_thread_local = threading.local()


def _session_hilo():
    s = getattr(_thread_local, "session", None)
    if s is None:
        s = requests.Session()
        _thread_local.session = s
    return s


def _http_get(session, url, **kwargs):
    """GET con reintentos ante 5xx / errores de red intermitentes."""
    ultimo = None
    for intento in range(REINTENTOS + 1):
        try:
            r = session.get(url, headers=HEADERS, timeout=TIMEOUT, **kwargs)
            if r.status_code >= 500:
                ultimo = requests.HTTPError(f"{r.status_code} Server Error: {url}")
                time.sleep(0.5 * (intento + 1))
                continue
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            ultimo = e
            time.sleep(0.5 * (intento + 1))
    raise ultimo


def api_get(session, path):
    r = _http_get(session, API + path)
    try:
        return r.json()
    except ValueError:
        return r.text


def _sumar_habiles(f, n):
    """Suma (o resta) n dias habiles a una fecha, salteando fines de semana."""
    paso = 1 if n > 0 else -1
    while n != 0:
        f = date.fromordinal(f.toordinal() + paso)
        if f.weekday() < 5:
            n -= paso
    return f


def resolver_fecha_boletin(session, numero, max_intentos=12):
    """
    Encuentra la fecha de publicacion del boletin N `numero`.
    La API solo consulta por FECHA, pero cada respuesta trae el numero y la
    fecha del boletin devuelto: con esa ancla se estima cuantos dias habiles
    hay que moverse y se itera hasta dar con el numero pedido (los feriados
    desvian la estimacion, pero cada consulta re-ancla y converge igual).
    Devuelve un date, o None si no se encontro.
    """
    fecha = date.today()
    consultadas = set()
    for _ in range(max_intentos):
        clave = fecha.strftime("%d-%m-%Y")
        if clave in consultadas:
            # Estimacion repetida (tipico alrededor de feriados): probar un
            # dia habil hacia atras para salir del bucle.
            fecha = _sumar_habiles(fecha, -1)
            continue
        consultadas.add(clave)
        try:
            data = api_get(session, f"/obtenerBoletin/{clave}/true")
        except Exception:
            fecha = _sumar_habiles(fecha, -1)
            continue
        if not isinstance(data, dict):
            return None
        b = data.get("boletin") if isinstance(data.get("boletin"), dict) else data
        try:
            n_actual = int(b.get("numero") or 0)
            f_actual = datetime.strptime(
                str(b.get("fecha_publicacion") or ""), "%d/%m/%Y").date()
        except (ValueError, AttributeError):
            return None
        if n_actual == numero:
            return f_actual
        fecha = _sumar_habiles(f_actual, numero - n_actual)
    return None


def extraer_ids(obj, encontrados=None):
    if encontrados is None:
        encontrados = {}
    if isinstance(obj, dict):
        id_val = None
        for k in ("id_norma", "id_documento", "iddocumento", "id", "documento_id"):
            if k in obj and isinstance(obj[k], (int, str)) and str(obj[k]).isdigit():
                id_val = int(obj[k])
                break
        if id_val and id_val > 10000:
            anexos_urls = []
            for ax in (obj.get("anexos") or []):
                if isinstance(ax, dict):
                    u = ax.get("filenet_firmado") or ax.get("url") or ""
                    if u:
                        anexos_urls.append(u)
            encontrados[id_val] = {
                "cita": str(obj.get("nombre") or "").strip(),
                "desc": str(obj.get("sumario") or obj.get("descripcion") or "").strip(),
                "url_norma": str(obj.get("url_norma") or "").strip(),
                "anexos": anexos_urls,
            }
        for v in obj.values():
            extraer_ids(v, encontrados)
    elif isinstance(obj, list):
        for item in obj:
            extraer_ids(item, encontrados)
    return encontrados


def _bajar_pdf_paginas(session, url):
    if not url:
        return []
    if url.startswith("http://"):
        url = "https://" + url[len("http://"):]
    r = _http_get(session, url)
    contenido = r.content
    if contenido[:4] == b"%PDF":
        try:
            with fitz.open(stream=contenido, filetype="pdf") as doc:
                return [p.get_text() for p in doc]
        except Exception:
            return []
    return [contenido.decode("utf-8", errors="ignore")]


def _slug(texto: str, max_len: int = 80) -> str:
    """Convierte una cita en un nombre de archivo seguro."""
    base = norm(texto).strip()
    base = re.sub(r"[^a-z0-9]+", "_", base).strip("_")
    return (base[:max_len] or "doc").rstrip("_")


def guardar_normativa(session, doc_id, info, relevancia, carpeta_dia):
    """
    Descarga y guarda en disco el PDF de la norma (y sus anexos) que matcheo,
    organizado por nivel de relevancia. Devuelve la lista de archivos creados.
    """
    destino = carpeta_dia / relevancia
    destino.mkdir(parents=True, exist_ok=True)
    base = f"{_slug(info.get('cita', '') or f'doc_{doc_id}')}__{doc_id}"

    objetivos = [("", info.get("url_norma", ""))]
    if INCLUIR_ANEXOS:
        for n, u in enumerate(info.get("anexos", []), 1):
            objetivos.append((f"_anexo{n}", u))

    creados = []
    for sufijo, url in objetivos:
        if not url:
            continue
        ruta = destino / f"{base}{sufijo}.pdf"
        if ruta.exists():
            creados.append(ruta)
            continue
        if url.startswith("http://"):
            url = "https://" + url[len("http://"):]
        try:
            r = _http_get(session, url)
            if r.content[:4] == b"%PDF":
                ruta.write_bytes(r.content)
                creados.append(ruta)
        except Exception as e:
            log(f"    (no se pudo guardar PDF de {doc_id}: {e})")
    return creados


def descargar_texto(session, doc_id, info):
    cache_file = CACHE_PDF / f"{doc_id}_pag.json"
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    fuentes = {}
    try:
        fuentes["Norma"] = _bajar_pdf_paginas(session, info.get("url_norma", ""))
    except Exception as e:
        log(f"    (norma {doc_id} no descargada: {e})")
        fuentes["Norma"] = []
    if INCLUIR_ANEXOS:
        for n, url_ax in enumerate(info.get("anexos", []), 1):
            try:
                fuentes[f"Anexo {n}"] = _bajar_pdf_paginas(session, url_ax)
            except Exception:
                fuentes[f"Anexo {n}"] = []
    cache_file.write_text(json.dumps(fuentes, ensure_ascii=False), encoding="utf-8")
    return fuentes


def buscar_keywords(fuentes, keywords_norm):
    hits = {}
    for fuente, paginas in fuentes.items():
        if not paginas:
            continue
        bucket = "cuerpo" if fuente == "Norma" else "anexo"
        for n_pag, texto in enumerate(paginas, 1):
            if not texto:
                continue
            texto_n = norm(texto)
            for kw_orig, kw_n, exacta in keywords_norm:
                palabras = kw_n.split()
                cierre = r"\b" if (exacta or not INCLUIR_VARIANTES) else r"\w*"
                partes_pat = [r"\b" + re.escape(p) + cierre for p in palabras]
                patron = r"\s+".join(partes_pat)
                for m in re.finditer(patron, texto_n):
                    ini = max(0, m.start() - CONTEXTO_CHARS)
                    fin = min(len(texto), m.end() + CONTEXTO_CHARS)
                    contexto = texto[ini:fin].replace("\n", " ").strip()
                    hits.setdefault(kw_orig, {"cuerpo": [], "anexo": []})
                    hits[kw_orig][bucket].append({
                        "fuente": fuente,
                        "pagina": n_pag,
                        "ctx": f"[{fuente}, p.{n_pag}] ...{contexto}...",
                    })
    return hits


# ----------------------------------------------------------------------
# SCORING DE RELEVANCIA
# ----------------------------------------------------------------------

def clasificar_relevancia(hits, descripcion="", cita=""):
    """
    Clasificacion por MATRIZ DE RIESGO POR MATERIA:
      1. El tema de mayor piso define de donde nace la norma (PISOS).
      2. Reglas del area legal: las Leyes y las designaciones/renuncias de
         Director General "para arriba" son siempre ALTA.
      3. Los agravantes (score) suben UN nivel como maximo (nunca fabrican
         ALTA desde rutina); una mencion debil solo en anexos baja MEDIA->BAJA.
    El score se conserva para ordenar dentro de cada nivel.
    """
    score = 0
    total_menciones = 0
    hay_cuerpo = False
    pagina_temprana = False
    for kw, b in hits.items():
        menciones = len(b["cuerpo"]) + len(b["anexo"])
        total_menciones += menciones
        if PISO_MATERIA.get(norm(kw)) == "ALTA":
            score += 2
        if b["cuerpo"]:
            hay_cuerpo = True
        for h in b["cuerpo"] + b["anexo"]:
            if h.get("pagina", 99) <= 3:
                pagina_temprana = True
    if hay_cuerpo:
        score += 2
    if total_menciones >= 5:
        score += 2
    if pagina_temprana:
        score += 1
    if len(hits) >= 2:
        score += 1

    # 1) Piso: el tema mas delicado manda. Materias no listadas (ej. busqueda
    #    libre de buscar_palabra.py) nacen en MEDIA.
    #    Anti-boilerplate: las materias de piso ALTA solo lo activan con una
    #    mencion SUSTANTIVA (el tema esta en el sumario, o se repite en el
    #    cuerpo). Una unica mencion suelta suele ser clausula estandar de
    #    contrato (ej. "proteccion de datos personales" en toda locacion).
    orden = ["BAJA", "MEDIA", "ALTA"]
    d = norm(descripcion or "")
    piso = 0
    for kw, b in hits.items():
        p = PISO_MATERIA.get(norm(kw), "MEDIA")
        if p == "ALTA":
            sustantiva = (norm(kw) in d) or len(b["cuerpo"]) >= 2
            if not sustantiva:
                p = "MEDIA"
        piso = max(piso, orden.index(p))

    # 2) Reglas del area legal
    if norm(cita or "").lstrip().startswith("ley"):
        piso = 2   # Leyes: siempre ALTA
    if RE_ACTO_PERSONAL.search(d) and RE_CARGO_ALTO.search(d):
        piso = 2   # designacion/renuncia de DG "para arriba"

    # 3) Ajuste por agravantes: un escalon como maximo
    nivel = piso
    if score >= 6 and nivel < 2:
        nivel += 1
    elif nivel == 1 and not hay_cuerpo and score <= 2:
        nivel = 0
    return orden[nivel], score


def generar_pdf(informe, ruta_pdf):
    """PDF ejecutivo: tablas por nivel de relevancia (ALTA/MEDIA/BAJA)."""
    if not REPORTLAB_OK:
        log("  (reportlab no instalado)")
        return None

    styles = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle("tit", parent=styles["Title"], fontSize=16)
    estilo_sub = ParagraphStyle("sub", parent=styles["Heading2"], fontSize=12)
    estilo_normal = ParagraphStyle("nor", parent=styles["Normal"], fontSize=9, leading=12)
    estilo_celda = ParagraphStyle("cel", parent=styles["Normal"], fontSize=8, leading=10)

    story = []
    dias = informe.get("dias", [])
    if len(dias) == 1:
        periodo = dias[0]["fecha"]
        nro = dias[0].get("nro_boletin", "")
        sub = f"Boletin N {nro} - {periodo}" if nro else periodo
    else:
        periodo = f"{dias[0]['fecha']} al {dias[-1]['fecha']}" if dias else "-"
        sub = f"Periodo: {periodo}"

    story.append(Paragraph("Monitoreo Normativo BOCBA", estilo_titulo))
    story.append(Paragraph(sub, estilo_sub))
    story.append(Paragraph(
        f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')} - "
        f"Etiquetas: {', '.join(informe.get('etiquetas', []) + informe.get('siglas', []))}",
        estilo_normal))
    story.append(Spacer(1, 0.4 * cm))

    todos = []
    for dia in dias:
        for h in dia.get("hallazgos", []):
            h = dict(h)
            h["_fecha"] = dia["fecha"]
            todos.append(h)

    if not todos:
        story.append(Paragraph("Sin coincidencias en el periodo analizado.", estilo_normal))
        SimpleDocTemplate(str(ruta_pdf), pagesize=A4).build(story)
        return ruta_pdf

    conteo = {"ALTA": 0, "MEDIA": 0, "BAJA": 0}
    for h in todos:
        conteo[h.get("relevancia", "BAJA")] = conteo.get(h.get("relevancia", "BAJA"), 0) + 1

    resumen = (f"Se detectaron <b>{len(todos)}</b> documentos con coincidencias: "
               f"<b>{conteo['ALTA']}</b> de relevancia ALTA, "
               f"<b>{conteo['MEDIA']}</b> MEDIA y <b>{conteo['BAJA']}</b> BAJA. "
               f"Se recomienda priorizar la revision de los documentos de relevancia ALTA.")
    story.append(Paragraph("Resumen ejecutivo", estilo_sub))
    story.append(Paragraph(resumen, estilo_normal))
    story.append(Spacer(1, 0.4 * cm))

    # Mismo semaforo que la app y la gacetilla (COLOR_RELEVANCIA).
    colores_nivel = {n: colors.HexColor(c) for n, c in COLOR_RELEVANCIA.items()}

    for nivel in ["ALTA", "MEDIA", "BAJA"]:
        docs = [h for h in todos if h.get("relevancia", "BAJA") == nivel]
        if not docs:
            continue
        docs.sort(key=lambda d: -d.get("score", 0))
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph(f"Relevancia {nivel} ({len(docs)})", estilo_sub))
        data = [[Paragraph("<b>Normativa</b>", estilo_celda),
                 Paragraph("<b>Etiquetas detectadas</b>", estilo_celda),
                 Paragraph("<b>Score</b>", estilo_celda)]]
        for d in docs:
            cita = d.get("cita") or f"Doc {d['doc_id']}"
            fecha_doc = d.get("_fecha", "")
            cita_full = f"{cita}<br/><font size=7 color='#666666'>{fecha_doc}</font>"
            etqs = []
            for k, b in d["keywords"].items():
                nc, na = len(b["cuerpo"]), len(b["anexo"])
                detalle = f"{nc}c" + (f"+{na}a" if na else "")
                etqs.append(f"{k} ({detalle})")
            data.append([
                Paragraph(cita_full, estilo_celda),
                Paragraph(", ".join(etqs), estilo_celda),
                Paragraph(str(d.get("score", "")), estilo_celda),
            ])
        tabla = Table(data, colWidths=[5.5 * cm, 9 * cm, 1.5 * cm], repeatRows=1)
        tabla.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colores_nivel[nivel]),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(tabla)

    story.append(Spacer(1, 0.5 * cm))
    nota = ("Nota metodologica: la relevancia se calcula con una matriz de scoring que "
            "pondera etiquetas de alto interes para auditoria TI, aparicion en el cuerpo "
            "normativo vs. anexos, cantidad de menciones y ubicacion en las primeras "
            "paginas. 'Nc' = menciones en cuerpo, 'Na' = en anexos.")
    story.append(Paragraph(nota, ParagraphStyle(
        "nota", parent=estilo_normal, fontSize=7, textColor=colors.HexColor("#888888"))))

    SimpleDocTemplate(str(ruta_pdf), pagesize=A4,
                      topMargin=1.5 * cm, bottomMargin=1.5 * cm,
                      leftMargin=1.5 * cm, rightMargin=1.5 * cm).build(story)
    return ruta_pdf


# ----------------------------------------------------------------------
# GACETILLA - PDF con identidad visual Obelisco V2 (GCBA)
# ----------------------------------------------------------------------
# Paleta y tipografia tomadas del sistema de diseno oficial Obelisco V2
# (https://gcba.github.io/Obelisco-V2).
OBELISCO = {
    "primary":   "#336ACC",
    "secondary": "#101E37",
    "tertiary":  "#005E7A",
    "dark":      "#002733",
    "body":      "#101E37",
    "body_sec":  "#38485C",
    "light":     "#F3F6F9",
    "neutral":   "#E6EBF0",
    "muted":     "#69788A",
    "success":   "#26874A",
    "warning":   "#FF9500",
    "error":     "#C62828",
    "info":      "#0086AD",
    "badge_bg":  "#ECF0F9",
}

# Semaforo de relevancia UNIFICADO: la app (KPIs, tabla, grafico), la gacetilla
# y el informe ejecutivo leen de aca. ALTA = alerta (rojo), no exito.
COLOR_RELEVANCIA = {
    "ALTA":  OBELISCO["error"],
    "MEDIA": OBELISCO["warning"],
    "BAJA":  OBELISCO["info"],
}

# Mapa sigla -> organismo emisor. Ampliable a medida que aparezcan nuevas siglas.
ORGANISMOS = {
    "MJGGC": "Jefatura de Gabinete de Ministros",
    "MHFGC": "Ministerio de Hacienda y Finanzas",
    "MEDGC": "Ministerio de Educación",
    "MCGC": "Ministerio de Cultura",
    "MEPHUGC": "Ministerio de Espacio Público e Higiene Urbana",
    "MSGC": "Ministerio de Salud",
    "MDHHGC": "Ministerio de Desarrollo Humano y Hábitat",
    "MJYSGC": "Ministerio de Justicia y Seguridad",
    "MDEPGC": "Ministerio de Desarrollo Económico y Producción",
    "MGEYA": "Mesa General de Entradas, Salidas y Archivo",
    "SECITD": "Secretaría de Innovación y Transformación Digital",
    "SECLYT": "Secretaría Legal y Técnica",
    "SSTEDU": "Subsecretaría (Educación)",
    "DGINFRAES": "Dirección General de Infraestructura Escolar",
    "DGIUR": "Dirección General de Interpretación Urbanística",
    "DGCYC": "Dirección General de Compras y Contrataciones",
    "DGEVA": "Dirección General de Evaluación",
    "DGPARE": "Dirección General de Proyectos de Arquitectura",
    "DGAYD": "Dirección General de Análisis y Datos",
    "DGAIGA": "Dirección General de Acceso a la Información y Gobierno Abierto",
    "ISSP": "Instituto Superior de Seguridad Pública",
    "EATC": "Ente Autárquico Teatro Colón",
    "FGAG": "Fiscalía General Adjunta de Gestión",
    "LOTBA": "Lotería de la Ciudad de Buenos Aires",
    "SGCBA": "Sindicatura General de la Ciudad",
    "OFIP": "Oficina de Integridad Pública",
    "APRA": "Agencia de Protección Ambiental",
    "AGC": "Agencia Gubernamental de Control",
    "ASINF": "Agencia de Sistemas de Información",
    "DGADCYP": "Dirección General Administrativa, Contable y Presupuesto",
    "DGEGP": "Dirección General de Educación de Gestión Privada",
    "DGCEME": "Dirección General de Cementerios",
    "DGGAYE": "Dirección General Guardia de Auxilio y Emergencias",
    "IRPS": "Instituto de Rehabilitación Psicofísica",
    "EAIT": "Ente Autárquico Instituto de Trasplante",
    "AGCBA": "Auditoría General de la Ciudad de Buenos Aires",
    "AGT": "Asesoría General Tutelar (Ministerio Público Tutelar)",
    "AGIP": "Administración Gubernamental de Ingresos Públicos",
    "CEO": "Comisión de Evaluación de Ofertas",
}

# Tipo de organismo inferido por el prefijo de la sigla, para las que todavia
# no estan mapeadas arriba (mejor "DGXXX - Direccion General" que la sigla
# sola). Orden = prioridad (prefijos mas especificos primero).
TIPOS_SIGLA = [
    ("DG", "Dirección General"),
    ("SSC", "Subsecretaría"),
    ("SS", "Subsecretaría"),
    ("SEC", "Secretaría"),
    ("UPE", "Unidad de Proyectos Especiales"),
    ("HG", "Hospital General"),
]


def titulo_organismo(cita: str) -> str:
    """Encabezado para la gacetilla: nombre real + sigla. Si la sigla no esta
    mapeada, al menos el tipo inferido por prefijo."""
    sig = sigla_de_cita(cita)
    if not sig:
        return "Otros organismos"
    nombre = ORGANISMOS.get(sig)
    if nombre:
        return f"{nombre} ({sig})"
    for pref, tipo in TIPOS_SIGLA:
        if sig.startswith(pref):
            return f"{sig} — {tipo}"
    return sig

# Patrones para inferir el TIPO DE ACTO desde el sumario. Orden = prioridad.
TIPOS_ACTO = [
    ("Designacion",          [r"design[a]", r"design[ae]se"]),
    ("Renuncia / Cese",      [r"acepta(?:r|se)?\s+la\s+renuncia", r"\brenuncia\b",
                              r"\bcesa(?:r|se)?\b", r"limita\s+los?\s+servicios"]),
    ("Cambio de estructura", [r"estructura\s+org", r"misiones?\s+y\s+funciones",
                              r"crea(?:r|se)?\s+la\s+(?:direccion|gerencia|unidad)",
                              r"modific[a]\s+la\s+estructura"]),
    ("Informe de gestion",   [r"informe\s+final\s+de\s+gestion"]),
    ("Contratacion",         [r"locacion\s+de\s+servicios", r"licitacion",
                              r"contratacion", r"adjudic", r"contrato"]),
    ("Ley / Normativa",      [r"\bley\b\s+n", r"aprueba\s+el\s+(?:plan|reglamento|"
                              r"protocolo|procedimiento|manual)"]),
]


def sigla_de_cita(cita: str) -> str:
    if not cita:
        return ""
    m = re.findall(r"/([A-Z]{2,})/", cita)
    if m:
        return m[0]
    m = re.findall(r"-([A-Z]{2,})/", cita)
    return m[0] if m else ""


def nombre_organismo(cita: str) -> str:
    sig = sigla_de_cita(cita)
    if not sig:
        return "Otros organismos"
    return ORGANISMOS.get(sig, sig)


def clasificar_acto(descripcion: str) -> str:
    txt = norm(descripcion or "")
    for etiqueta, patrones in TIPOS_ACTO:
        for p in patrones:
            if re.search(p, txt):
                return etiqueta
    return "Otro"


def _registrar_fuentes():
    """
    Registra Nunito (titulos) y Open Sans (cuerpo) si los TTF estan disponibles.
    Busca primero en la carpeta local 'fonts/' del proyecto (dejar ahi las fuentes
    oficiales del GCBA); si no estan, intenta Poppins del sistema; si no, Helvetica.
    """
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    base = Path(__file__).parent / "fonts"
    candidatos = [Path("/usr/share/fonts/truetype/google-fonts"),
                  Path("/usr/share/fonts/truetype")]

    def _try(nombre, *rutas):
        for r in rutas:
            if r and Path(r).exists():
                try:
                    pdfmetrics.registerFont(TTFont(nombre, str(r)))
                    return True
                except Exception:
                    pass
        return False

    f = {"titulo": "Helvetica", "titulo_bold": "Helvetica-Bold",
         "cuerpo": "Helvetica", "cuerpo_bold": "Helvetica-Bold"}

    ok_t = _try("Nunito", base / "Nunito-Regular.ttf")
    ok_tb = _try("Nunito-Bold", base / "Nunito-Bold.ttf", base / "Nunito-SemiBold.ttf")
    ok_c = _try("OpenSans", base / "OpenSans-Regular.ttf")
    ok_cb = _try("OpenSans-Bold", base / "OpenSans-SemiBold.ttf", base / "OpenSans-Bold.ttf")

    if not ok_t:
        for d in candidatos:
            if _try("Nunito", d / "Poppins-Regular.ttf"):
                ok_t = True
                break
    if not ok_tb:
        for d in candidatos:
            if _try("Nunito-Bold", d / "Poppins-Bold.ttf", d / "Poppins-Medium.ttf"):
                ok_tb = True
                break

    if ok_t:
        f["titulo"] = "Nunito"
    if ok_tb:
        f["titulo_bold"] = "Nunito-Bold"
    if ok_c:
        f["cuerpo"] = "OpenSans"
    if ok_cb:
        f["cuerpo_bold"] = "OpenSans-Bold"
    return f


def generar_pdf_gacetilla(informe, ruta_pdf):
    """
    GACETILLA NORMATIVA en PDF con identidad visual Obelisco V2.
    Vista de lectura: agrupa por organismo emisor; de cada norma muestra tipo de
    acto, descripcion (sumario), semaforo de relevancia y enlace VER BOCBA.
    """
    if not REPORTLAB_OK:
        log("  (reportlab no instalado)")
        return None

    from reportlab.platypus import HRFlowable

    F = _registrar_fuentes()
    C = {k: colors.HexColor(v) for k, v in OBELISCO.items()}

    st_masthead = ParagraphStyle("mh", fontName=F["titulo_bold"], fontSize=26,
                                 textColor=colors.white, leading=30)
    st_masthead_sub = ParagraphStyle("mhs", fontName=F["cuerpo"], fontSize=10,
                                     textColor=colors.HexColor("#CCE0FF"), leading=14)
    st_meta = ParagraphStyle("meta", fontName=F["cuerpo"], fontSize=9,
                             textColor=C["muted"], leading=13)
    st_intro = ParagraphStyle("intro", fontName=F["cuerpo"], fontSize=10.5,
                              textColor=C["body_sec"], leading=16)
    st_org = ParagraphStyle("org", fontName=F["titulo_bold"], fontSize=14,
                            textColor=C["secondary"], leading=18)
    st_cita = ParagraphStyle("cita", fontName=F["titulo_bold"], fontSize=11,
                             textColor=C["body"], leading=15)
    st_acto = ParagraphStyle("acto", fontName=F["cuerpo_bold"], fontSize=8,
                             textColor=C["tertiary"], leading=11)
    st_desc = ParagraphStyle("desc", fontName=F["cuerpo"], fontSize=9.5,
                             textColor=C["body_sec"], leading=14)
    st_ver = ParagraphStyle("ver", fontName=F["cuerpo_bold"], fontSize=9,
                            textColor=C["primary"], leading=13)
    st_pie = ParagraphStyle("pie", fontName=F["cuerpo"], fontSize=7.5,
                            textColor=C["muted"], leading=11)

    def badge(nivel):
        col = COLOR_RELEVANCIA.get(nivel, OBELISCO["info"])
        txt = (f'<font name="{F["cuerpo_bold"]}" color="{col}" size="8">'
               f'[ {nivel} ]</font>')
        return Paragraph(txt, ParagraphStyle("bdg", fontName=F["cuerpo"],
                                             fontSize=8, leading=11, alignment=2))

    story = []
    dias = informe.get("dias", [])
    if dias and len(dias) == 1:
        periodo = dias[0]["fecha"]
        nro = dias[0].get("nro_boletin", "")
    elif dias:
        periodo = f'{dias[0]["fecha"]} al {dias[-1]["fecha"]}'
        nro = ""
    else:
        periodo, nro = "-", ""

    cab = Table(
        [[Paragraph("Gacetilla Normativa", st_masthead)],
         [Paragraph("Gobierno de la Ciudad Autonoma de Buenos Aires - "
                    "Monitoreo del Boletin Oficial", st_masthead_sub)]],
        colWidths=[18 * cm])
    cab.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C["dark"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 16),
        ("RIGHTPADDING", (0, 0), (-1, -1), 16),
        ("TOPPADDING", (0, 0), (0, 0), 16),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 14),
        ("TOPPADDING", (0, 1), (-1, 1), 2),
    ]))
    story.append(cab)
    story.append(HRFlowable(width="100%", thickness=4, color=C["primary"],
                            spaceBefore=0, spaceAfter=10))

    sub = f"Boletin N {nro} - {periodo}" if nro else f"Periodo: {periodo}"
    story.append(Paragraph(
        f"{sub} - Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}", st_meta))
    story.append(Spacer(1, 0.3 * cm))

    todos = []
    for dia in dias:
        for h in dia.get("hallazgos", []):
            it = dict(h)
            it["_fecha"] = dia.get("fecha", "")
            it["_boletin"] = dia.get("nro_boletin", "")
            todos.append(it)

    if not todos:
        story.append(Paragraph("Sin novedades en el periodo analizado.", st_intro))
        SimpleDocTemplate(str(ruta_pdf), pagesize=A4,
                          topMargin=1.2 * cm, bottomMargin=1.4 * cm,
                          leftMargin=1.5 * cm, rightMargin=1.5 * cm).build(story)
        return ruta_pdf

    conteo = {"ALTA": 0, "MEDIA": 0, "BAJA": 0}
    for h in todos:
        conteo[h.get("relevancia", "BAJA")] = conteo.get(h.get("relevancia", "BAJA"), 0) + 1

    intro = (f"Se detectaron <b>{len(todos)}</b> normas de interes segun los criterios "
             f"de auditoria, tecnologia, datos y control interno: "
             f"{conteo['ALTA']} de relevancia alta, {conteo['MEDIA']} media y "
             f"{conteo['BAJA']} baja. Las novedades se presentan agrupadas por "
             f"organismo emisor.")
    caja = Table([[Paragraph(intro, st_intro)]], colWidths=[18 * cm])
    caja.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C["light"]),
        ("LINEBEFORE", (0, 0), (0, -1), 3, C["primary"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(caja)
    story.append(Spacer(1, 0.5 * cm))

    orden_rel = {"ALTA": 0, "MEDIA": 1, "BAJA": 2}
    grupos = {}
    for h in todos:
        grupos.setdefault(titulo_organismo(h.get("cita", "")), []).append(h)

    def peso_org(items):
        return (min(orden_rel.get(i.get("relevancia", "BAJA"), 3) for i in items),)
    organismos_ordenados = sorted(grupos.items(), key=lambda kv: (peso_org(kv[1]), kv[0]))

    for org, items in organismos_ordenados:
        items.sort(key=lambda d: (orden_rel.get(d.get("relevancia", "BAJA"), 3),
                                  -d.get("score", 0)))
        head = Table([[Paragraph(org.upper(), st_org)]], colWidths=[18 * cm])
        head.setStyle(TableStyle([
            ("LINEBEFORE", (0, 0), (0, -1), 4, C["tertiary"]),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(head)
        story.append(Spacer(1, 0.2 * cm))

        for d in items:
            cita = d.get("cita") or f"Documento {d.get('doc_id')}"
            desc = d.get("descripcion") or "Sin descripcion disponible."
            tipo = clasificar_acto(desc)
            url = d.get("url", "")
            meta = f"BOCBA {d.get('_boletin') or 's/n'} - {d.get('_fecha','')}"

            # Ancho total = ancho de la tarjeta (16.4) MENOS el padding
            # izquierdo+derecho (12pt + 12pt ~ 0.85 cm); si se pasa, el badge
            # de relevancia queda dibujado FUERA del recuadro.
            fila_top = Table(
                [[Paragraph(cita, st_cita), badge(d.get("relevancia", "BAJA"))]],
                colWidths=[12.85 * cm, 2.7 * cm])
            fila_top.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]))

            ver = (f'<a href="{url}"><font color="#336ACC">VER BOCBA &gt;</font></a>'
                   if url else "")
            sep = "&nbsp;&nbsp;-&nbsp;&nbsp;" if ver else ""
            contenido = [
                [fila_top],
                [Paragraph(tipo.upper(), st_acto)],
                [Paragraph(desc, st_desc)],
                [Paragraph(f'{ver}<font color="#69788A" size="7.5">{sep}{meta}</font>',
                           st_ver)],
            ]
            card = Table(contenido, colWidths=[16.4 * cm])
            card.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.6, C["neutral"]),
                ("LINEBEFORE", (0, 0), (0, -1), 3,
                 colors.HexColor(COLOR_RELEVANCIA.get(d.get("relevancia", "BAJA"),
                                                      OBELISCO["info"]))),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (0, 0), 9),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 9),
                ("TOPPADDING", (0, 1), (-1, -1), 2),
            ]))
            story.append(card)
            story.append(Spacer(1, 0.25 * cm))

        story.append(Spacer(1, 0.3 * cm))

    story.append(HRFlowable(width="100%", thickness=0.6, color=C["neutral"],
                            spaceBefore=4, spaceAfter=6))
    story.append(Paragraph(
        "Gacetilla generada automaticamente a partir de fuentes publicas del Boletin "
        "Oficial de la Ciudad de Buenos Aires. El tipo de acto y la relevancia son "
        "inferidos por la herramienta y requieren validacion. Identidad visual basada "
        "en el sistema de diseno Obelisco V2 (GCBA).",
        st_pie))

    SimpleDocTemplate(str(ruta_pdf), pagesize=A4,
                      topMargin=1.2 * cm, bottomMargin=1.4 * cm,
                      leftMargin=1.5 * cm, rightMargin=1.5 * cm).build(story)
    return ruta_pdf


# ----------------------------------------------------------------------
# GACETILLA "EDICION INSTITUCIONAL" - solo ALTA, lista para circular
# ----------------------------------------------------------------------
# Version curada inspirada en la gacetilla semanal institucional de la
# SGCBA: encabezado tipo tarjeta, fecha en espanol, bandas de color por
# seccion y cada norma con su numero linkeado + sumario.

_DIAS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes",
            "sábado", "domingo"]
_MESES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
             "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _fecha_es(f):
    """date -> 'jueves 2 de julio de 2026'."""
    return f"{_DIAS_ES[f.weekday()]} {f.day} de {_MESES_ES[f.month - 1]} de {f.year}"


_SECCIONES_ORDEN = ["PODER LEGISLATIVO", "PODER EJECUTIVO",
                    "ÓRGANOS DE CONTROL", "PODER JUDICIAL Y MINISTERIO PÚBLICO"]


def _seccion_de_cita(cita):
    """Seccion institucional inferida desde la cita (aproximada por sigla)."""
    if norm(cita or "").lstrip().startswith("ley"):
        return "PODER LEGISLATIVO"
    sig = sigla_de_cita(cita)
    if sig in {"SGCBA", "AGCBA"}:
        return "ÓRGANOS DE CONTROL"
    if sig in {"AGT", "CMCABA", "TSJ", "FG", "FGAG", "MPF", "MPD"}:
        return "PODER JUDICIAL Y MINISTERIO PÚBLICO"
    return "PODER EJECUTIVO"


def generar_pdf_gacetilla_institucional(informe, ruta_pdf):
    """
    Edicion institucional: SOLO las normas de relevancia ALTA (la seleccion
    curada), agrupadas por seccion y organismo. Pensada para circular por
    mail. Complementa a la gacetilla completa (estilo Obelisco).
    """
    if not REPORTLAB_OK:
        log("  (reportlab no instalado)")
        return None

    from reportlab.platypus import HRFlowable

    F = _registrar_fuentes()
    VERDE = colors.HexColor("#34D399")
    AZUL = colors.HexColor("#1D4E89")
    CUERPO = colors.HexColor("#101E37")
    GRIS = colors.HexColor("#69788A")

    st_titulo = ParagraphStyle("it", fontName=F["titulo_bold"], fontSize=22,
                               textColor=CUERPO, alignment=1, leading=26)
    st_fecha = ParagraphStyle("if", fontName=F["cuerpo_bold"], fontSize=12,
                              textColor=CUERPO, alignment=1, leading=16)
    st_intro = ParagraphStyle("ii", fontName=F["cuerpo"], fontSize=10.5,
                              textColor=CUERPO, alignment=1, leading=16)
    st_banda = ParagraphStyle("ib", fontName=F["cuerpo_bold"], fontSize=12,
                              textColor=CUERPO, alignment=1, leading=15)
    st_org = ParagraphStyle("io", fontName=F["titulo_bold"], fontSize=12.5,
                            textColor=CUERPO, leading=16, spaceBefore=10)
    st_norma = ParagraphStyle("in", fontName=F["cuerpo_bold"], fontSize=10.5,
                              textColor=AZUL, leading=14, spaceBefore=5)
    st_sumario = ParagraphStyle("is", fontName=F["cuerpo"], fontSize=10,
                                textColor=CUERPO, leading=14.5)
    st_pie = ParagraphStyle("ip", fontName=F["cuerpo"], fontSize=7.5,
                            textColor=GRIS, leading=11)

    # Fechas del periodo, en espanol
    fechas = []
    for d in informe.get("dias", []):
        try:
            fechas.append(datetime.strptime(d.get("fecha", ""),
                                            "%d/%m/%Y").date())
        except ValueError:
            pass
    if len(fechas) == 1:
        sub = f"Edición del {_fecha_es(fechas[0])}"
    elif fechas:
        sub = (f"Edición del {fechas[0].day} de "
               f"{_MESES_ES[fechas[0].month - 1]} al {fechas[-1].day} de "
               f"{_MESES_ES[fechas[-1].month - 1]} de {fechas[-1].year}")
    else:
        sub = "Edición"

    # Solo ALTA (la seleccion curada; las reglas del area legal ya caen aca)
    altas = []
    for dia in informe.get("dias", []):
        for h in dia.get("hallazgos", []):
            if h.get("relevancia") == "ALTA":
                it = dict(h)
                it["_fecha"] = dia.get("fecha", "")
                it["_boletin"] = dia.get("nro_boletin", "")
                altas.append(it)

    story = []

    # Encabezado: tarjeta con borde redondeado
    cab = Table(
        [[Paragraph("GACETILLA NORMATIVA", st_titulo)],
         [Paragraph(sub, st_fecha)],
         [Paragraph("Selección de las novedades de mayor relevancia "
                    "publicadas en el Boletín Oficial de la Ciudad de "
                    "Buenos Aires, según los criterios de auditoría, "
                    "tecnología, datos y control interno.", st_intro)]],
        colWidths=[17 * cm])
    cab.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1.6, AZUL),
        ("ROUNDEDCORNERS", [14, 14, 14, 14]),
        ("LEFTPADDING", (0, 0), (-1, -1), 22),
        ("RIGHTPADDING", (0, 0), (-1, -1), 22),
        ("TOPPADDING", (0, 0), (0, 0), 16),
        ("TOPPADDING", (0, 1), (-1, 1), 6),
        ("TOPPADDING", (0, 2), (-1, 2), 8),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 16),
    ]))
    story.append(cab)
    story.append(Spacer(1, 0.7 * cm))

    if not altas:
        story.append(Paragraph("Sin normas de relevancia alta en el "
                               "período analizado.", st_sumario))
    else:
        # Agrupar: seccion -> organismo -> normas (por score)
        grupos = {}
        for h in altas:
            sec = _seccion_de_cita(h.get("cita", ""))
            org = titulo_organismo(h.get("cita", ""))
            grupos.setdefault(sec, {}).setdefault(org, []).append(h)

        for sec in _SECCIONES_ORDEN:
            if sec not in grupos:
                continue
            banda = Table([[Paragraph(sec, st_banda)]], colWidths=[17 * cm])
            banda.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), VERDE),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(Spacer(1, 0.35 * cm))
            story.append(banda)
            story.append(Spacer(1, 0.15 * cm))

            for org in sorted(grupos[sec]):
                story.append(Paragraph(org, st_org))
                items = sorted(grupos[sec][org],
                               key=lambda d: -d.get("score", 0))
                for d in items:
                    cita = d.get("cita") or f"Documento {d.get('doc_id')}"
                    url = d.get("url", "")
                    if url:
                        texto_cita = (f'<a href="{url}"><u>{cita}</u></a>'
                                      f'<font color="#69788A" size="8">'
                                      f'&nbsp;&nbsp;(BOCBA '
                                      f'{d.get("_boletin") or "s/n"} - '
                                      f'{d.get("_fecha", "")})</font>')
                    else:
                        texto_cita = cita
                    story.append(Paragraph(texto_cita, st_norma))
                    story.append(Paragraph(
                        d.get("descripcion") or "Sin descripción disponible.",
                        st_sumario))

    story.append(Spacer(1, 0.7 * cm))
    story.append(HRFlowable(width="100%", thickness=0.6,
                            color=colors.HexColor("#E6EBF0")))
    story.append(Paragraph(
        "Edición generada automáticamente a partir de fuentes públicas del "
        "Boletín Oficial de la Ciudad de Buenos Aires. Incluye únicamente "
        "las normas clasificadas de relevancia ALTA por la matriz de riesgo "
        "por materia; la selección es inferida y requiere validación "
        "profesional. Herramienta no oficial.", st_pie))

    SimpleDocTemplate(str(ruta_pdf), pagesize=A4,
                      topMargin=1.4 * cm, bottomMargin=1.4 * cm,
                      leftMargin=2 * cm, rightMargin=2 * cm).build(story)
    return ruta_pdf


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------

def procesar_dia(session, fecha, keywords_norm):
    fecha_disp = fecha.replace("-", "/")
    log("-" * 60)
    log(f"DIA {fecha_disp}")

    try:
        boletin = api_get(session, f"/obtenerBoletin/{fecha}/true")
    except Exception as e:
        log(f"  ERROR consultando boletin: {e}")
        return {"fecha": fecha_disp, "error": str(e), "hallazgos": []}

    nro = ""
    fecha_pub = ""
    if isinstance(boletin, dict):
        # El numero viene anidado: {"boletin": {"numero": 7388, ...}, ...}
        b = boletin.get("boletin") if isinstance(boletin.get("boletin"), dict) else boletin
        nro = (b.get("numero") or b.get("nro_boletin") or b.get("nroBoletin")
               or boletin.get("numero") or boletin.get("nro_boletin") or "")
        fecha_pub = str(b.get("fecha_publicacion") or "").strip()
    log(f"  Boletin Nro: {nro or '(no detectado)'}")

    # La API devuelve el ULTIMO boletin publicado cuando la fecha pedida no
    # tiene boletin propio (fin de semana / feriado). Sin este control, el
    # mismo boletin se procesaria y contaria varias veces en un rango.
    # Se corta ANTES de escribir el raw: si no, queda en disco un JSON con
    # el boletin del viernes "disfrazado" de sabado/domingo.
    if fecha_pub and fecha_pub != fecha_disp:
        log(f"  Sin boletin propio este dia (la API devolvio el del "
            f"{fecha_pub}). Dia omitido.")
        return {"fecha": fecha_disp, "nro_boletin": "", "docs_analizados": 0,
                "hallazgos": [], "sin_boletin": True}

    (CARPETA / f"raw_boletin_{fecha}.json").write_text(
        json.dumps(boletin, ensure_ascii=False, indent=2), encoding="utf-8")

    try:
        secciones = api_get(session, f"/obtenerSeccionesBoletin/{fecha}")
        (CARPETA / f"raw_secciones_{fecha}.json").write_text(
            json.dumps(secciones, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        log(f"  (no se pudo obtener secciones: {e})")
        secciones = {}

    ids = {}
    ids.update(extraer_ids(boletin))
    ids.update(extraer_ids(secciones))
    log(f"  Documentos detectados: {len(ids)}")

    if not ids:
        log("  No se detectaron IDs. Revisar raw_*.json para ajustar extraer_ids().")
        return {"fecha": fecha_disp, "nro_boletin": nro,
                "docs_analizados": 0, "hallazgos": []}

    res_dia = {"fecha": fecha_disp, "nro_boletin": nro,
               "docs_analizados": 0, "hallazgos": []}
    total = len(ids)
    carpeta_dia = NORMATIVAS / fecha

    def procesar_doc(i, doc_id, info):
        """Descarga, busca y (si matchea) guarda el PDF. Devuelve dict o None."""
        session_h = _session_hilo()
        cita = info.get("cita", "")
        desc = info.get("desc", "")
        try:
            texto = descargar_texto(session_h, doc_id, info)
        except Exception as e:
            log(f"    [{i}/{total}] ERROR doc {doc_id}: {e}")
            return ("error", None)

        if not any(p.strip() for paginas in texto.values() for p in paginas):
            return ("analizado", None)

        hits = buscar_keywords(texto, keywords_norm)
        if not hits:
            return ("analizado", None)

        etiqueta_doc = cita if cita else (desc[:60] if desc else f"Doc {doc_id}")
        relevancia, score = clasificar_relevancia(hits)
        partes_log = []
        for k, b in hits.items():
            nc, na = len(b["cuerpo"]), len(b["anexo"])
            detalle = f"{nc}c" + (f"+{na}a" if na else "")
            partes_log.append(f"{k} ({detalle})")
        log(f"    [{i}/{total}] >> [{relevancia}] {etiqueta_doc}: "
            f"{', '.join(partes_log)}")

        archivos = []
        if GUARDAR_NORMATIVAS:
            archivos = guardar_normativa(session_h, doc_id, info, relevancia, carpeta_dia)

        return ("analizado", {
            "doc_id": doc_id,
            "cita": cita,
            "descripcion": desc,
            "relevancia": relevancia,
            "score": score,
            "url": info.get("url_norma") or f"{API}/getUrlDocument/{doc_id}/4",
            "anexos_urls": list(info.get("anexos", [])),
            "archivos": [str(a) for a in archivos],
            "keywords": {k: {"cuerpo": v["cuerpo"][:3], "anexo": v["anexo"][:3]}
                         for k, v in hits.items()},
        })

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futuros = [ex.submit(procesar_doc, i, doc_id, info)
                   for i, (doc_id, info) in enumerate(ids.items(), 1)]
        for fut in as_completed(futuros):
            estado, hallazgo = fut.result()
            if estado != "error":
                res_dia["docs_analizados"] += 1
            if hallazgo:
                res_dia["hallazgos"].append(hallazgo)

    res_dia["hallazgos"].sort(key=lambda d: -d.get("score", 0))
    if GUARDAR_NORMATIVAS and res_dia["hallazgos"]:
        log(f"  Normativas guardadas en: {carpeta_dia}")
    return res_dia


def imprimir_gacetilla_consola(informe):
    print("\n" + "=" * 60)
    print("GACETILLA NORMATIVA AUTOMATIZADA")
    print("=" * 60)

    dias = informe.get("dias", [])
    if not dias:
        print("Sin datos para informar.")
        return

    fecha = dias[0].get("fecha", "")
    print()
    print("Novedades detectadas en el Boletin Oficial de la Ciudad de Buenos Aires")
    print("segun los criterios definidos para auditoria, tecnologia, datos y control.")
    print()
    print(f"Comunicacion automatica. {fecha}")
    print()

    todos = []
    for dia in dias:
        for h in dia.get("hallazgos", []):
            item = dict(h)
            item["_fecha"] = dia.get("fecha", "")
            item["_boletin"] = dia.get("nro_boletin", "")
            todos.append(item)

    orden = {"ALTA": 0, "MEDIA": 1, "BAJA": 2}
    todos = sorted(todos, key=lambda x: (orden.get(x.get("relevancia", "BAJA"), 3),
                                         -x.get("score", 0)))

    for nivel in ["ALTA", "MEDIA", "BAJA"]:
        docs = [d for d in todos if d.get("relevancia") == nivel]
        if not docs:
            continue
        print()
        print(f"RELEVANCIA {nivel}")
        print("-" * 60)
        for d in docs:
            cita = d.get("cita") or f"Documento {d.get('doc_id')}"
            descripcion = d.get("descripcion") or "Sin descripcion disponible."
            url = d.get("url", "")
            etiquetas = []
            for k, b in d.get("keywords", {}).items():
                nc = len(b.get("cuerpo", []))
                na = len(b.get("anexo", []))
                detalle = []
                if nc:
                    detalle.append(f"{nc} en cuerpo")
                if na:
                    detalle.append(f"{na} en anexo")
                if detalle:
                    etiquetas.append(f"{k} ({', '.join(detalle)})")
            print()
            print(cita)
            print(descripcion)
            print(f"Etiquetas detectadas: {', '.join(etiquetas)}")
            print(f"(BOCBA {d.get('_boletin') or 's/n'} - {d.get('_fecha')})")
            print(f"VER BOCBA: {url}")


def main():
    fechas = rango_fechas()
    CARPETA.mkdir(exist_ok=True)
    CACHE_PDF.mkdir(parents=True, exist_ok=True)
    if GUARDAR_NORMATIVAS:
        NORMATIVAS.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    keywords_norm = [(k, norm(k), False) for k in KEYWORDS]
    keywords_norm += [(s, norm(s), True) for s in SIGLAS]
    for concepto, variantes in SINONIMOS.items():
        for v in variantes:
            keywords_norm.append((concepto, norm(v), False))

    log("=" * 60)
    log("MONITOR BOCBA v2 - busqueda directa en PDFs del boletin")
    if len(fechas) == 1:
        log(f"Fecha: {fechas[0].replace('-', '/')}")
    else:
        log(f"Rango: {fechas[0].replace('-','/')} a {fechas[-1].replace('-','/')} "
            f"({len(fechas)} dias)")
    log(f"Terminos: {', '.join(KEYWORDS)}")
    log(f"Siglas (exactas): {', '.join(SIGLAS)}")
    log(f"Conceptos con sinonimos: {', '.join(SINONIMOS.keys())}")
    log(f"Descargas en paralelo: {MAX_WORKERS} | Guardar normativas: {GUARDAR_NORMATIVAS}")
    log("=" * 60)

    informe = {
        "ejecucion": datetime.now().isoformat(),
        "etiquetas": KEYWORDS,
        "siglas": SIGLAS,
        "sinonimos": SINONIMOS,
        "dias": [],
    }

    for fecha in fechas:
        res_dia = procesar_dia(session, fecha, keywords_norm)
        informe["dias"].append(res_dia)

    tag = (f"{fechas[0]}" if len(fechas) == 1 else f"{fechas[0]}_a_{fechas[-1]}")
    salida = CARPETA / f"reporte_{tag}.json"
    salida.write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 60)
    print("RESUMEN CONSOLIDADO")
    print("=" * 60)

    total_hits = 0
    por_etiqueta = {}
    orden_rel = {"ALTA": 0, "MEDIA": 1, "BAJA": 2}
    conteo_rel = {"ALTA": 0, "MEDIA": 0, "BAJA": 0}

    for dia in informe["dias"]:
        h = dia.get("hallazgos", [])
        if not h:
            continue
        h_ordenado = sorted(h, key=lambda d: (orden_rel.get(d.get("relevancia", "BAJA"), 3),
                                              -d.get("score", 0)))
        print(f"\n### {dia['fecha']} - Boletin {dia.get('nro_boletin','?')} "
              f"- {len(h)} documento(s) con coincidencias:")
        for d in h_ordenado:
            total_hits += 1
            rel = d.get("relevancia", "BAJA")
            conteo_rel[rel] = conteo_rel.get(rel, 0) + 1
            partes = []
            tiene_cuerpo = False
            for k, b in d["keywords"].items():
                nc, na = len(b["cuerpo"]), len(b["anexo"])
                if nc:
                    tiene_cuerpo = True
                detalle = f"{nc} cuerpo" + (f" + {na} anexo" if na else "")
                partes.append(f"{k} ({detalle})")
                pe = por_etiqueta.setdefault(k, [0, 0])
                pe[0] += nc
                pe[1] += na
            titulo = d.get("cita") or f"Doc {d['doc_id']}"
            marca = "" if tiene_cuerpo else "  [solo en anexos]"
            print(f"  [{rel}] {titulo}{marca}")
            print(f"      {', '.join(partes)}")
            print(f"      {d['url']}")
            for k, b in d["keywords"].items():
                ej = (b["cuerpo"] or b["anexo"])
                if ej:
                    print(f"      Ej: {ej[0]['ctx'][:160]}")
                    break

    print("\n" + "-" * 60)
    if total_hits == 0:
        print("Sin coincidencias en el periodo analizado.")
    else:
        print(f"Total documentos con coincidencias: {total_hits}")
        print(f"Relevancia: {conteo_rel['ALTA']} ALTA, "
              f"{conteo_rel['MEDIA']} MEDIA, {conteo_rel['BAJA']} BAJA")
        print("\nPor etiqueta (cuerpo normativo / anexos):")
        for k, (nc, na) in sorted(por_etiqueta.items(), key=lambda x: -(x[1][0]+x[1][1])):
            print(f"  - {k}: {nc} en cuerpo, {na} en anexos  (total {nc+na})")
    # Rutas ABSOLUTAS: la terminal de VS Code las convierte en links
    # (Ctrl+Click); las relativas no siempre las reconoce.
    print(f"\nReporte completo: {salida.resolve()}")
    print(f"PDFs cacheados en: {CACHE_PDF.resolve()}")
    if GUARDAR_NORMATIVAS and total_hits:
        print(f"Normativas que matchearon (PDF): {NORMATIVAS.resolve()}")

    # Si un PDF esta abierto en el visor, Windows lo bloquea y la escritura
    # falla: avisamos y seguimos con los demas (clave para que la corrida
    # automatica del Programador de tareas nunca muera por esto).
    for generador, ruta, etiqueta in (
            (generar_pdf, CARPETA / f"informe_{tag}.pdf",
             "Informe PDF ejecutivo"),
            (generar_pdf_gacetilla, CARPETA / f"gacetilla_{tag}.pdf",
             "Gacetilla PDF"),
            (generar_pdf_gacetilla_institucional,
             CARPETA / f"gacetilla_institucional_{tag}.pdf",
             "Gacetilla institucional (solo ALTA)")):
        try:
            if generador(informe, ruta):
                print(f"{etiqueta}: {ruta.resolve()}")
        except PermissionError:
            print(f"AVISO: no se pudo escribir {ruta.name} porque esta "
                  f"ABIERTO en el visor de PDF. Cerralo y volve a correr "
                  f"el monitor (el resto se genero igual).")


if __name__ == "__main__":
    main()
