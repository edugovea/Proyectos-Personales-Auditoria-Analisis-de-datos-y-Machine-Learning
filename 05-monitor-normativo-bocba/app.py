"""
Monitor Normativo BOCBA - Interfaz web (Streamlit)
==================================================
Lee los reportes JSON que genera monitor_bocba_v2.py (carpeta reportes_bocba/)
y los muestra en un tablero con filtros, KPIs, tabla y descarga de PDF.

No vuelve a llamar a la API: trabaja sobre lo ya procesado por el monitor.
Para actualizar datos, corre el monitor y despues refresca la app.

Uso:
  py -m streamlit run app.py
"""

import json
import re
import subprocess
import tempfile
from datetime import date, datetime, time as dtime, timedelta
from pathlib import Path

import requests

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# Reutilizamos la logica del monitor (organismos + generacion de gacetilla PDF).
# Importar el modulo NO ejecuta el scraping: main() solo corre desde consola.
import monitor_bocba_v2 as mon

DIR_PROY = Path(__file__).parent
CARPETA = DIR_PROY / "reportes_bocba"

# --- Automatizacion (Windows Task Scheduler) ---
TASK_NAME = "MonitorBOCBA_Diario"
BAT_AUTO = DIR_PROY / "automatizar_bocba.bat"


def _schtasks(args):
    """Llama a schtasks sin shell (evita problemas de comillas/rutas)."""
    return subprocess.run(["schtasks", *args], capture_output=True, text=True,
                          encoding="cp850", errors="replace")


def estado_automatizacion():
    """Devuelve (activo, proxima_ejecucion) de la tarea diaria del monitor."""
    r = _schtasks(["/Query", "/TN", TASK_NAME, "/FO", "CSV", "/NH"])
    if r.returncode != 0:
        return False, ""
    campos = [c.strip('"') for c in r.stdout.strip().split('","')]
    return True, (campos[1] if len(campos) > 1 else "")


def activar_automatizacion(hhmm):
    """Crea/actualiza la tarea diaria. Genera un .bat correcto (ruta real, sin
    pause) que corre el monitor y guarda log."""
    bat = (f'@echo off\r\nchcp 65001 >nul\r\ncd /d "{DIR_PROY}"\r\n'
           f'py -X utf8 monitor_bocba_v2.py '
           f'>> "reportes_bocba\\log_automatizacion.txt" 2>&1\r\n')
    BAT_AUTO.write_text(bat, encoding="ascii")
    r = _schtasks(["/Create", "/SC", "DAILY", "/ST", hhmm, "/TN", TASK_NAME,
                   "/TR", f'"{BAT_AUTO}"', "/F"])
    return r.returncode == 0, (r.stdout + r.stderr).strip()


def desactivar_automatizacion():
    r = _schtasks(["/Delete", "/TN", TASK_NAME, "/F"])
    return r.returncode == 0, (r.stdout + r.stderr).strip()

ORDEN_REL = {"ALTA": 0, "MEDIA": 1, "BAJA": 2}

# Etiquetas con su ortografia correcta (con tildes). Clave = forma sin tilde/
# minusculas (mon.norm). Se usa para mostrar prolijo aunque el reporte las
# haya guardado sin tilde.
LABEL_TILDE = {
    "auditoria": "auditoría",
    "contratacion": "Contratación",
    "designacion de personal": "Designación de personal",
    "digitalizacion": "digitalización",
    "sistema informatico": "sistema informático",
    "seguridad informatica": "seguridad informática",
    "analisis y datos": "Análisis y Datos",
}


def normalizar_keywords(kws):
    """Reportes viejos guardan cada mencion como texto; los nuevos como dict
    {fuente, pagina, ctx}. Unificamos todo al formato dict para poder reusar
    clasificar_relevancia() del monitor."""
    norm = {}
    for kw, buckets in kws.items():
        nb = {"cuerpo": [], "anexo": []}
        for tipo in ("cuerpo", "anexo"):
            for item in buckets.get(tipo, []):
                if isinstance(item, dict):
                    nb[tipo].append(item)
                else:  # string tipo "[Anexo 1, p.3] ...texto..."
                    m = re.search(r"p\.(\d+)", item)
                    nb[tipo].append({
                        "ctx": item,
                        "pagina": int(m.group(1)) if m else 99,
                        "fuente": "",
                    })
        norm[kw] = nb
    return norm

st.set_page_config(page_title="Monitor Normativo BOCBA",
                   page_icon="📑", layout="wide")

# Identidad visual OBELISCO V2 (GCBA): tipografia Archivo + Open Sans, paleta
# oficial, expanders con aspecto de boton y KPIs tipo tarjeta.
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Archivo:wght@400;600;700&family=Open+Sans:wght@400;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap');

/* Tipografia Obelisco */
html, body, .stApp, [data-testid="stAppViewContainer"],
[data-testid="stSidebar"] { font-family: 'Open Sans', sans-serif; }
h1, h2, h3, h4, h5, h6 { font-family: 'Archivo', sans-serif; }

/* Iconos Material Symbols (los que usa Obelisco V2) para el HTML propio
   (masthead, footer, callouts). Los widgets usan :material/...: nativo. */
.ms {
    font-family: 'Material Symbols Outlined';
    font-weight: 400; font-style: normal; line-height: 1;
    display: inline-block; vertical-align: -0.15em;
    font-variation-settings: 'FILL' 1;
}

/* Menos aire muerto arriba, pero sin que el header fijo de Streamlit
   tape el masthead (con menos de ~3.5rem el titulo queda cortado). */
.block-container { padding-top: 3.5rem; }

/* Boton primario (Buscar / Activar) con elevacion */
button[kind="primary"] {
    box-shadow: 0 2px 6px rgba(51, 106, 204, 0.30);
}
button[kind="primary"]:hover {
    box-shadow: 0 4px 12px rgba(51, 106, 204, 0.42);
}

/* Expanders del sidebar (Automatizar / Cuando / Que / Como) con look de boton
   primario Obelisco */
section[data-testid="stSidebar"] details {
    border: none !important;
    background: transparent !important;
    margin-bottom: 0.5rem;
}
section[data-testid="stSidebar"] details summary {
    background: #336ACC;
    border-radius: 0.5rem;
    padding: 0.55rem 0.85rem;
    font-family: 'Archivo', sans-serif;
    font-weight: 600;
    cursor: pointer;
    list-style: none;
}
section[data-testid="stSidebar"] details summary:hover {
    background: #2B59AD;
}
section[data-testid="stSidebar"] details summary * ,
section[data-testid="stSidebar"] details summary p {
    color: #FFFFFF !important;
    font-weight: 600;
}
section[data-testid="stSidebar"] details summary svg {
    fill: #FFFFFF !important;
    color: #FFFFFF !important;
}

/* KPIs (st.metric) como tarjetas Obelisco */
[data-testid="stMetric"] {
    background: rgba(127, 140, 160, 0.08);
    border: 1px solid rgba(127, 140, 160, 0.22);
    border-radius: 0.6rem;
    padding: 0.9rem 1.1rem;
}
[data-testid="stMetricValue"] {
    font-family: 'Archivo', sans-serif;
    color: #336ACC;
}

/* Scrollbars discretas: la barra nativa de Windows es gruesa, siempre
   visible y tapa contenido del sidebar. */
::-webkit-scrollbar { width: 9px; height: 9px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
    background: rgba(127, 140, 160, 0.45);
    border-radius: 5px;
}
::-webkit-scrollbar-thumb:hover { background: rgba(127, 140, 160, 0.7); }

/* Borde de color del semaforo en cada tarjeta KPI (containers con key) */
.st-key-kpi_alta  [data-testid="stMetric"] { border-left: 4px solid #C62828; }
.st-key-kpi_media [data-testid="stMetric"] { border-left: 4px solid #FF9500; }
.st-key-kpi_baja  [data-testid="stMetric"] { border-left: 4px solid #0086AD; }
</style>
""", unsafe_allow_html=True)


def masthead():
    """Cabecera institucional estilo Obelisco (banda oscura + borde primary)."""
    st.markdown("""
    <div style="background:#002733;border-radius:0.6rem;
                border-bottom:4px solid #336ACC;padding:1.1rem 1.4rem;
                margin-bottom:1.1rem;">
      <div style="font-family:'Archivo',sans-serif;font-weight:700;font-size:28px;
                  color:#FFFFFF;line-height:1.15;">
        <span class="ms" style="font-size:30px;color:#CCE0FF;">policy</span>
        Monitor Normativo BOCBA</div>
      <div style="font-family:'Open Sans',sans-serif;font-size:13.5px;
                  color:#CCE0FF;margin-top:0.3rem;">
        Gobierno de la Ciudad de Buenos Aires · Vigilancia del Boletín Oficial
        — auditoría, tecnología, datos y control interno
      </div>
    </div>
    """, unsafe_allow_html=True)


def footer():
    """Pie institucional estilo Obelisco: banda oscura espejo del masthead."""
    st.markdown("""
    <div style="background:#002733;border-radius:0.6rem;
                border-top:4px solid #336ACC;padding:1.1rem 1.4rem;
                margin-top:1.6rem;">
      <div style="font-family:'Archivo',sans-serif;font-weight:600;font-size:13px;
                  color:#FFFFFF;">
        <span class="ms" style="font-size:15px;color:#CCE0FF;">policy</span>
        Monitor Normativo BOCBA</div>
      <div style="font-family:'Open Sans',sans-serif;font-size:11.5px;
                  color:#CCE0FF;margin-top:0.35rem;line-height:1.55;">
        Fuente: Boletín Oficial de la Ciudad Autónoma de Buenos Aires
        (información pública). La relevancia y el tipo de acto son inferidos
        automáticamente por la herramienta y requieren validación profesional.
      </div>
    </div>
    """, unsafe_allow_html=True)


def callout(texto, icono="info"):
    """Aviso estilo Obelisco: fondo claro + borde izquierdo primary."""
    st.markdown(f"""
    <div style="background:#F3F6F9;border-left:3px solid #336ACC;
                border-radius:0.4rem;padding:0.85rem 1.1rem;color:#101E37;
                font-size:0.93rem;font-family:'Open Sans',sans-serif;">
      <span class="ms" style="color:#336ACC;margin-right:7px;">{icono}</span>{texto}
    </div>
    """, unsafe_allow_html=True)


def bienvenida(rango_txt, ultima):
    """Pantalla inicial: solo el saludo y la guia, sin resultados ni KPIs."""
    extra = f" · Última ejecución del monitor: {ultima}" if ultima else ""
    st.markdown(f"""
    <div style="background:#F3F6F9;border-left:4px solid #336ACC;
                border-radius:0.6rem;padding:1.7rem 1.9rem;margin-top:0.5rem;
                color:#101E37;font-family:'Open Sans',sans-serif;">
      <div style="font-family:'Archivo',sans-serif;font-weight:700;
                  font-size:25px;color:#101E37;">
        <span class="ms" style="font-size:27px;color:#336ACC;">waving_hand</span>
        Bienvenido, ¿qué necesitás hoy?</div>
      <div style="margin-top:0.9rem;font-size:14.5px;line-height:1.75;">
        Buscá normativa del Boletín Oficial desde el panel de la izquierda:
        <br>&bull; <b>Cuándo</b>: tocá <b>&ldquo;Hoy&rdquo;</b>,
        <b>&ldquo;Esta semana&rdquo;</b> o <b>&ldquo;Rango completo&rdquo;</b>
        (abre el calendario para elegir las fechas que quieras).
        <br>&bull; <b>Qué</b>: filtrá por relevancia, temas o cualquier
        palabra clave — o buscá directo por <b>número de boletín</b> (si no
        está en la biblioteca, la app te ofrece traerlo del BOCBA al momento).
        <br>&bull; Cuando estés listo, tocá <b>Buscar</b>.
      </div>
      <div style="margin-top:1rem;padding:0.65rem 0.95rem;background:#ECF0F9;
                  border-radius:0.45rem;font-size:13px;color:#101E37;
                  line-height:1.6;">
        <span class="ms" style="color:#336ACC;margin-right:5px;">info</span>
        <b>Importante:</b> si automatizaste el BOCBA, tocá el botón
        <b>&ldquo;Actualizar datos&rdquo;</b> del panel izquierdo para cargar
        lo que el monitor procesó por su cuenta.
      </div>
      <div style="margin-top:0.9rem;font-size:12px;color:#69788A;">
        Datos disponibles: {rango_txt}{extra}
      </div>
    </div>
    """, unsafe_allow_html=True)


def badge_rel(nivel):
    """Chip de relevancia con el semaforo unificado del monitor."""
    col = mon.COLOR_RELEVANCIA.get(nivel, "#69788A")
    return (f'<span style="background:{col}1A;color:{col};border-radius:999px;'
            f'padding:2px 10px;font-size:12px;font-weight:700;'
            f'font-family:\'Open Sans\',sans-serif;">{nivel}</span>')


# ----------------------------------------------------------------------
# CARGA DE DATOS
# ----------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def cargar_datos():
    """Aplana todos los reporte_*.json en un DataFrame (dedup por fecha+doc)."""
    filas, vistos = [], set()
    etiquetas, siglas = list(mon.KEYWORDS), list(mon.SIGLAS)
    ultima_ejec = ""   # timestamp ISO de la corrida mas reciente del monitor

    # Fallback del N° de boletin: los reportes viejos lo guardaron vacio, pero
    # el JSON crudo de la API si lo tiene (anidado en boletin.numero).
    raw_nums = {}
    for rf in CARPETA.glob("raw_boletin_*.json"):
        try:
            rb = json.loads(rf.read_text(encoding="utf-8"))
            b = rb.get("boletin") if isinstance(rb.get("boletin"), dict) else rb
            num = b.get("numero") or b.get("nro_boletin") or ""
            if num:
                raw_nums[rf.stem.replace("raw_boletin_", "").replace("-", "/")] = str(num)
        except Exception:
            pass

    # Mapa doc_id -> URLs de anexos (para el link "Ver anexo"). Sale del JSON
    # crudo de la API, que si trae las URLs (los reportes viejos no las guardan).
    anexos_por_doc = {}
    for rf in list(CARPETA.glob("raw_boletin_*.json")) + \
              list(CARPETA.glob("raw_secciones_*.json")):
        try:
            rb = json.loads(rf.read_text(encoding="utf-8"))
            for did, info in mon.extraer_ids(rb).items():
                for u in (info.get("anexos") or []):
                    anexos_por_doc.setdefault(did, [])
                    if u and u not in anexos_por_doc[did]:
                        anexos_por_doc[did].append(u)
        except Exception:
            pass

    for jf in sorted(CARPETA.glob("reporte_*.json")):
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
        except Exception:
            continue
        etiquetas = data.get("etiquetas", etiquetas)
        siglas = data.get("siglas", siglas)
        # ISO 8601 compara bien como texto: nos quedamos con la mas nueva.
        ultima_ejec = max(ultima_ejec, data.get("ejecucion", "") or "")
        for dia in data.get("dias", []):
            fecha = dia.get("fecha", "")
            boletin = str(dia.get("nro_boletin") or "") or raw_nums.get(fecha, "")
            for h in dia.get("hallazgos", []):
                clave = (fecha, h.get("doc_id"))
                if clave in vistos:
                    continue
                vistos.add(clave)
                kws = normalizar_keywords(h.get("keywords", {}))
                archivos = h.get("archivos", [])
                # URLs de anexos: del reporte nuevo si estan, si no del raw.
                anexos_urls = (h.get("anexos_urls")
                               or anexos_por_doc.get(h.get("doc_id"), []))
                anexo_url = (anexos_urls[0] if anexos_urls else "")
                if anexo_url.startswith("http://"):
                    anexo_url = "https://" + anexo_url[len("http://"):]
                tiene_anexo = (bool(anexos_urls)
                               or any("_anexo" in a.lower() for a in archivos)
                               or any(b.get("anexo") for b in kws.values()))
                menciones = sum(len(b.get("cuerpo", [])) + len(b.get("anexo", []))
                                for b in kws.values())
                # Recalculamos SIEMPRE con la matriz de riesgo vigente (pisos
                # por materia + reglas del area legal): asi todo el historico
                # queda clasificado con el mismo criterio, aunque el reporte
                # traiga guardada una relevancia de una version anterior.
                relevancia, score = mon.clasificar_relevancia(
                    kws, h.get("descripcion", ""), h.get("cita", ""))
                h = {**h, "relevancia": relevancia, "score": score}
                try:
                    fecha_dt = pd.to_datetime(fecha, format="%d/%m/%Y").date()
                except Exception:
                    fecha_dt = None
                filas.append({
                    "fecha": fecha,
                    "fecha_dt": fecha_dt,
                    "nro_boletin": str(boletin or ""),
                    "doc_id": h.get("doc_id"),
                    "cita": h.get("cita") or f"Doc {h.get('doc_id')}",
                    "organismo": mon.nombre_organismo(h.get("cita", "")),
                    "descripcion": h.get("descripcion", ""),
                    "relevancia": relevancia or "BAJA",
                    "score": score or 0,
                    "etiquetas": list(kws.keys()),
                    "menciones": menciones,
                    "anexo": tiene_anexo,
                    "anexo_url": anexo_url,
                    "url": h.get("url", ""),
                    "_raw": h,
                    "_kws": kws,   # menciones ya normalizadas (para el detalle)
                })
    df = pd.DataFrame(filas)

    # Unifica etiquetas que solo difieren por tildes (reportes viejos las
    # guardaron con tilde y el monitor nuevo sin tilde). Se muestra una sola,
    # prefiriendo la version CON tilde (auditoria/auditoría -> auditoría).
    if not df.empty:
        todas = {e for lst in df["etiquetas"] for e in lst}
        grupos = {}
        for e in todas:
            grupos.setdefault(mon.norm(e), []).append(e)
        canon = {}
        for k, variantes in grupos.items():
            con_tilde = [v for v in variantes if any(ord(c) > 127 for c in v)]
            elegido = (LABEL_TILDE.get(k)
                       or sorted(con_tilde or variantes, key=lambda x: (-len(x), x))[0])
            for v in variantes:
                canon[v] = elegido
        df["etiquetas"] = df["etiquetas"].apply(
            lambda lst: sorted({canon[e] for e in lst}))

    ultima = ""
    if ultima_ejec:
        try:
            ultima = datetime.fromisoformat(ultima_ejec).strftime("%d/%m/%Y %H:%M")
        except ValueError:
            ultima = ultima_ejec
    return df, etiquetas, siglas, ultima


def informe_desde_df(fdf, etiquetas, siglas):
    """Reconstruye la estructura que espera generar_pdf_gacetilla, ya filtrada."""
    dias_map = {}
    for _, row in fdf.iterrows():
        dias_map.setdefault((row["fecha"], row["nro_boletin"]), []).append(row["_raw"])
    dias = [{"fecha": f, "nro_boletin": b, "hallazgos": hs}
            for (f, b), hs in dias_map.items()]
    return {"etiquetas": etiquetas, "siglas": siglas, "dias": dias}


@st.cache_data(show_spinner=False)
def generar_gacetilla_bytes(informe):
    """Genera la gacetilla PDF (reutiliza reportlab del monitor) y la devuelve en bytes."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        ruta = Path(tmp.name)
    mon.generar_pdf_gacetilla(informe, ruta)
    datos = ruta.read_bytes()
    try:
        ruta.unlink()
    except Exception:
        pass
    return datos


def traer_boletin(numero):
    """
    Busqueda EN VIVO por numero de boletin: resuelve la fecha contra la API,
    procesa el boletin con el criterio completo del monitor y lo incorpora a
    la biblioteca de la app (mismo flujo que buscar_bocba.py, pero sin salir
    del tablero). Bloquea la app los minutos que dure la descarga.
    """
    with st.status(f"Buscando el Boletín N° {numero} en el BOCBA…",
                   expanded=True) as status:
        session = requests.Session()
        st.write("Resolviendo la fecha de publicación…")
        fecha = mon.resolver_fecha_boletin(session, numero)
        if fecha is None:
            status.update(label=f"No se encontró el Boletín N° {numero} "
                                "(¿número correcto?)", state="error")
            return
        st.write(f"Boletín N° {numero} → publicado el "
                 f"**{fecha.strftime('%d/%m/%Y')}**. Descargando y "
                 "analizando (2-4 min si no está en caché)…")
        kws = [(k, mon.norm(k), False) for k in mon.KEYWORDS]
        kws += [(s, mon.norm(s), True) for s in mon.SIGLAS]
        for concepto, variantes in mon.SINONIMOS.items():
            for v in variantes:
                kws.append((concepto, mon.norm(v), False))
        res = mon.procesar_dia(session, fecha.strftime("%d-%m-%Y"), kws)
        informe = {"ejecucion": datetime.now().isoformat(),
                   "etiquetas": mon.KEYWORDS, "siglas": mon.SIGLAS,
                   "dias": [res]}
        salida = CARPETA / f"reporte_{fecha.strftime('%d-%m-%Y')}.json"
        salida.write_text(json.dumps(informe, ensure_ascii=False, indent=2),
                          encoding="utf-8")
        status.update(label=f"Boletín N° {numero} incorporado: "
                            f"{len(res.get('hallazgos', []))} hallazgos",
                      state="complete")
    # Pedir limpieza del filtro de fechas para la proxima corrida (no se
    # puede tocar el estado de un widget ya instanciado en esta) y recargar
    # los datos para que el boletin nuevo aparezca ya mismo.
    st.session_state["reset_fechas_pend"] = True
    st.cache_data.clear()
    st.rerun()


@st.cache_data(show_spinner=False)
def generar_institucional_bytes(informe):
    """Edicion institucional (solo ALTA), lista para circular por mail."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        ruta = Path(tmp.name)
    mon.generar_pdf_gacetilla_institucional(informe, ruta)
    datos = ruta.read_bytes()
    try:
        ruta.unlink()
    except Exception:
        pass
    return datos


# ----------------------------------------------------------------------
# APP
# ----------------------------------------------------------------------
with st.spinner("Cargando reportes…"):
    df, ETIQUETAS, SIGLAS, ULTIMA_EJEC = cargar_datos()

masthead()

if df.empty:
    st.warning("No hay reportes en `reportes_bocba/`. Corré primero el monitor:  "
               "`py monitor_bocba_v2.py`", icon=":material/folder_off:")
    footer()
    st.stop()

fecha_min = min(d for d in df["fecha_dt"] if d)
fecha_max = max(d for d in df["fecha_dt"] if d)

# "Generacion" de filtros: al Reiniciar busqueda se incrementa y TODOS los
# widgets renacen con keys nuevas -> vuelven a sus defaults de forma
# confiable. (Borrar las keys a mano no alcanza: el navegador a veces
# "resucita" los valores viejos en la siguiente interaccion.)
GEN = st.session_state.setdefault("filtros_gen", 0)


def K(nombre):
    """Key de widget versionada por generacion de filtros."""
    return f"{nombre}_{GEN}"


def _activar_busqueda():
    """Cualquier interaccion con un filtro saca la pantalla de bienvenida."""
    st.session_state["busqueda_activa"] = True


def _aplicar_rapida():
    """Atajos de fecha: activan la busqueda. 'Rango completo' ademas
    despliega el calendario (vacio) para elegir fechas a medida."""
    st.session_state["busqueda_activa"] = True
    if st.session_state.get(K("f_rapida")) == "Rango completo":
        st.session_state[K("f_rango")] = ()


# Reset de fechas pedido por traer_boletin(): se aplica ACA, antes de que
# los widgets se instancien (despues ya no se puede tocar su estado).
if st.session_state.pop("reset_fechas_pend", False):
    st.session_state[K("f_rapida")] = None
    st.session_state[K("f_rango")] = ()

# Calendario VACIO por defecto (sin filtro de fecha hasta que el usuario
# elija). Si quedo un rango guardado que ya no entra en los datos, se limpia.
if K("f_rango") not in st.session_state:
    st.session_state[K("f_rango")] = ()
else:
    try:
        _ok = all(fecha_min <= d <= fecha_max
                  for d in st.session_state[K("f_rango")])
    except TypeError:
        _ok = False
    if not _ok:
        st.session_state[K("f_rango")] = ()

# ---------------- SIDEBAR: FILTROS ----------------
with st.sidebar:
    st.header("Filtros")

    # ---------------- AUTOMATIZACIÓN (arriba, siempre a mano) ----------------
    with st.expander("Automatizar", icon=":material/smart_toy:", expanded=False):
        activo, proxima = estado_automatizacion()
        if activo:
            st.success(f"Activada ✅\n\nPróxima ejecución: **{proxima}**")
            st.caption("Todos los días corre el monitor sobre el boletín del día "
                       "y actualiza los reportes automáticamente.")
            if st.button("Desactivar automatización", use_container_width=True):
                ok, msg = desactivar_automatizacion()
                if ok:
                    st.toast("Automatización desactivada")
                    st.rerun()
                else:
                    st.error(msg)
        else:
            st.write("Programá una búsqueda **diaria** automática del BOCBA.")
            hora = st.time_input("Hora", value=dtime(7, 0), step=1800)
            if st.button("Activar automatización", type="primary",
                         use_container_width=True):
                ok, msg = activar_automatizacion(hora.strftime("%H:%M"))
                if ok:
                    st.toast("Automatización activada")
                    st.rerun()
                else:
                    st.error(f"No se pudo activar:\n\n{msg}")
        st.caption("Usa el Programador de tareas de Windows. No requiere que la "
                   "app quede abierta.")

    with st.expander("Cuándo", icon=":material/calendar_month:", expanded=True):
        rapida = st.segmented_control(
            "Búsqueda rápida", ["Hoy", "Esta semana", "Rango completo"],
            default=None, key=K("f_rapida"), on_change=_aplicar_rapida,
            help="'Hoy' y 'Esta semana' usan el último boletín disponible. "
                 "'Rango completo' abre el calendario para elegir las fechas "
                 "que quieras.")
        desde = hasta = None
        if rapida == "Hoy":
            desde = hasta = fecha_max
            st.caption(f"Buscando en el boletín del "
                       f"**{fecha_max.strftime('%d/%m/%Y')}**")
        elif rapida == "Esta semana":
            desde = max(fecha_min,
                        fecha_max - timedelta(days=fecha_max.weekday()))
            hasta = fecha_max
            st.caption(f"Buscando del **{desde.strftime('%d/%m/%Y')}** al "
                       f"**{hasta.strftime('%d/%m/%Y')}**")
        elif rapida == "Rango completo":
            # El calendario aparece SOLO en este modo. Arranca vacio: sin
            # fechas elegidas no se filtra (se busca en todo lo disponible).
            rango = st.date_input(
                "Rango de fechas", min_value=fecha_min, max_value=fecha_max,
                format="DD/MM/YYYY", key=K("f_rango"),
                on_change=_activar_busqueda,
                help="Vacío = busca en todas las fechas disponibles.")
            if isinstance(rango, (list, tuple)) and len(rango) == 2:
                desde, hasta = rango
                if desde > hasta:
                    desde, hasta = hasta, desde

    with st.expander("Qué", icon=":material/search:", expanded=False):
        # Sin seleccion por defecto: el usuario decide si filtra o no.
        # Nada elegido (o 'TODAS') = se muestran los tres niveles.
        sel_rel = st.pills(
            "Relevancia", ["TODAS", "ALTA", "MEDIA", "BAJA"],
            selection_mode="multi", default=None, key=K("f_rel"),
            on_change=_activar_busqueda,
            help="Elegí una o varias (como en Excel). Sin selección o "
                 "'TODAS' = los tres niveles.")
        niveles = (["ALTA", "MEDIA", "BAJA"]
                   if (not sel_rel or "TODAS" in sel_rel) else sel_rel)
        etiquetas_disp = sorted({e for lst in df["etiquetas"] for e in lst})
        etiquetas_sel = st.multiselect("Etiquetas / temas", etiquetas_disp,
                                       placeholder="Todas", key=K("f_etiquetas"),
                                       on_change=_activar_busqueda)
        # Autocompletado: sugiere etiquetas + terminos comunes, pero permite
        # escribir cualquier palabra libre (accept_new_options). Se deduplica
        # ignorando mayus/minus (para no repetir Contratación/contratación).
        extra = {"contrato", "beca", "licitación", "designación", "renuncia",
                 "convenio", "resolución", "disposición", "adjudicación",
                 "subsidio"}
        _vistos = {}
        for s in list(etiquetas_disp) + sorted(extra):
            _vistos.setdefault(s.casefold(), s)  # 1ro gana -> etiqueta con tilde
        sugerencias = sorted(_vistos.values(), key=str.casefold)
        palabra = st.selectbox("Palabra clave", sugerencias, index=None,
                               accept_new_options=True, key=K("f_palabra"),
                               on_change=_activar_busqueda,
                               placeholder="Escribí o elegí… (ej: aud → auditoría)")
        nro_bol = st.text_input("N° de Boletín", placeholder="ej: 7234",
                                key=K("f_boletin"),
                                on_change=_activar_busqueda)

    with st.expander("Cómo", icon=":material/tune:", expanded=False):
        anexo_f = st.segmented_control("Anexos", ["Todas", "Con Anexo", "Sin Anexo"],
                                       default="Todas", key=K("f_anexos"),
                                       on_change=_activar_busqueda)

    st.divider()
    # Buscar siempre a la vista, coherente con la guia de la bienvenida.
    # Desde la bienvenida muestra los resultados; con la busqueda ya activa
    # es inocuo (los filtros se aplican solos), pero da la confirmacion
    # explicita que el usuario espera.
    if st.button("Buscar", icon=":material/search:", type="primary",
                 use_container_width=True,
                 help="Muestra los resultados con los filtros elegidos "
                      "(sin filtros, muestra todo)."):
        st.session_state["busqueda_activa"] = True

    # Los filtros se aplican solos al tocarlos (Streamlit re-ejecuta). Este
    # boton relee los JSON de reportes_bocba/ (el cache no expira solo, asi
    # que si el monitor corrio con la app abierta, los datos nuevos no
    # aparecen hasta refrescar).
    if st.button("Actualizar datos", icon=":material/refresh:",
                 use_container_width=True,
                 help="Relee los reportes de `reportes_bocba/`. Usalo si el "
                      "monitor corrió mientras la app estaba abierta."):
        st.cache_data.clear()
        st.rerun()

    # Vuelve todos los filtros a su estado inicial: borra el estado de cada
    # widget (recuperan su default al re-crearse) y cambia la key del grid
    # para limpiar tambien los filtros de columna de la tabla.
    if st.button("Reiniciar búsqueda", icon=":material/restart_alt:",
                 use_container_width=True,
                 help="Borra todos los filtros y vuelve a la pantalla de "
                      "bienvenida."):
        # Nueva generacion de filtros: todos los widgets renacen con keys
        # nuevas y sus valores por defecto (reset a prueba de resurrecciones).
        st.session_state["filtros_gen"] = GEN + 1
        st.session_state["grid_reset"] = st.session_state.get("grid_reset", 0) + 1
        st.session_state["busqueda_activa"] = False
        st.rerun()

# ---------------- BIENVENIDA: antes de la primera busqueda ----------------
# La app arranca "en blanco": solo el saludo. Los resultados aparecen cuando
# el usuario toca un filtro, un atajo o el boton Buscar.
if not st.session_state.get("busqueda_activa"):
    bienvenida(f"{fecha_min.strftime('%d/%m/%Y')} – "
               f"{fecha_max.strftime('%d/%m/%Y')}", ULTIMA_EJEC)
    footer()
    st.stop()

st.caption(f":material/event_available: Datos al "
           f"**{fecha_max.strftime('%d/%m/%Y')}**"
           + (f" · Última ejecución del monitor: {ULTIMA_EJEC}"
              if ULTIMA_EJEC else ""))

# ---------------- FILTRADO ----------------
f = df.copy()
if desde and hasta:
    f = f[f["fecha_dt"].between(desde, hasta)]
if niveles:
    f = f[f["relevancia"].isin(niveles)]
if etiquetas_sel:
    f = f[f["etiquetas"].apply(lambda lst: any(e in lst for e in etiquetas_sel))]
if palabra:
    p = mon.norm(palabra)  # sin tildes / minusculas: "auditoria" == "auditoría"
    f = f[f["cita"].apply(lambda x: p in mon.norm(x))
          | f["descripcion"].apply(lambda x: p in mon.norm(x or ""))
          | f["etiquetas"].apply(lambda lst: any(p in mon.norm(e) for e in lst))]
if nro_bol.strip():
    f = f[f["nro_boletin"].str.contains(nro_bol.strip(), na=False)]
if anexo_f == "Con Anexo":
    f = f[f["anexo"]]
elif anexo_f == "Sin Anexo":
    f = f[~f["anexo"]]

f = f.sort_values(by=["relevancia", "score"],
                  key=lambda s: s.map(ORDEN_REL) if s.name == "relevancia" else -s)

# ---------------- RESUMEN OPCIONAL (plegado): el buscador es el protagonista
with st.expander("Indicadores del período (KPIs)",
                 icon=":material/monitoring:"):
    c1, c2, c3 = st.columns(3)
    with c1, st.container(key="kpi_alta"):
        st.metric("Alta relevancia", int((f["relevancia"] == "ALTA").sum()))
    with c2, st.container(key="kpi_media"):
        st.metric("Media relevancia", int((f["relevancia"] == "MEDIA").sum()))
    with c3, st.container(key="kpi_baja"):
        st.metric("Baja relevancia", int((f["relevancia"] == "BAJA").sum()))

with st.expander("Cómo se calcula la relevancia",
                 icon=":material/calculate:"):
    st.markdown("""
La clasificación usa una **matriz de riesgo por materia** (definida en
`monitor_bocba_v2.py`): el tema define el piso del que nace cada norma, y
los agravantes ajustan como máximo un nivel.

**1 · Piso por materia** — el tema más delicado manda:

| Nace en | Materias |
|---|---|
| **ALTA** | datos personales, ciberseguridad, seguridad informática, control interno, auditoría, Sindicatura General (SGCBA), DGAYD, OFIP, acceso a la información, transparencia activa (DGAIGA), informes finales de gestión, cambios de estructura |
| **MEDIA** | inteligencia artificial, sistemas informáticos, digitalización, Análisis y Datos, contrataciones, mesa de entradas, Ley de Modernización |
| **BAJA** | designaciones y renuncias/ceses de rutina |

**2 · Reglas del área legal** — son siempre **ALTA**: las **Leyes** y las
designaciones/renuncias de **Director General "para arriba"** (DG,
subsecretarios, secretarios, ministros, autoridades fuera de nivel).

**3 · Agravantes (score)** — mención en el cuerpo (+2), materia de piso ALTA
(+2 c/u), 5+ menciones (+2), primeras 3 páginas (+1), 2+ materias (+1).
Con **6 o más puntos la norma sube un nivel** (nunca dos); una mención débil
solo en anexos baja de MEDIA a BAJA. El score ordena dentro de cada nivel.
""")

# ---------------- RESULTADOS ----------------
st.subheader(
    ":material/table_view: Resultados",
    help="La tabla funciona como un Excel: ordená clickeando el encabezado de "
         "cualquier columna, buscá con la lupa 🔍 y ampliá a pantalla completa ⛶ "
         "(barra que aparece arriba a la derecha de la tabla al pasar el mouse). "
         "Para filtrar por relevancia, fecha, etiqueta o anexo, usá el panel de "
         "la izquierda.")

if f.empty:
    nro_txt = nro_bol.strip()
    if nro_txt.isdigit():
        # Busqueda por numero de boletin sin resultados: probablemente ese
        # boletin nunca fue procesado -> ofrecer traerlo EN VIVO del BOCBA.
        callout(f"El Boletín N° {nro_txt} no está en la biblioteca local "
                "(todavía no fue procesado por el monitor). Podés traerlo "
                "ahora mismo del BOCBA.", icono="cloud_download")
        st.write("")
        if st.button(f"Buscar el Boletín N° {nro_txt} en el BOCBA",
                     icon=":material/cloud_download:", type="primary"):
            traer_boletin(int(nro_txt))
    else:
        callout("No se encontraron normas con estos filtros. "
                "Probá ampliar el rango de fechas o quitar alguna condición.",
                icono="search_off")
else:
    tabla = pd.DataFrame({
        "Fecha": f["fecha"],
        "Relevancia": f["relevancia"],
        "Normativa": f["cita"],
        "Organismo": f["organismo"],
        "Descripción": f["descripcion"],
        "Etiquetas": f["etiquetas"].apply(lambda lst: ", ".join(lst)),
        "Boletín": f["nro_boletin"].replace("", "s/n"),
        "BOCBA": f["url"],
        "Anexo": f["anexo_url"],   # URL directa al PDF del anexo (o "")
        "Score": f["score"],
    })

    # Filtro de texto que ignora tildes y mayus/minus (como el buscador del
    # sidebar). "contratacion" matchea "Contratación".
    matcher_sin_tilde = JsCode("""
        function(params){
          const norm = s => (s==null?'':s.toString())
              .normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase();
          const t = norm(params.filterText);
          return t === '' || norm(params.value).indexOf(t) >= 0;
        }""")

    # Tabla tipo Excel (AgGrid): UNA cajita de filtro por columna (sin el embudo
    # ni el menu), orden clickeando el encabezado, columnas redimensionables.
    gob = GridOptionsBuilder.from_dataframe(tabla)
    # Seleccion multiple con click: cada fila clickeada queda sombreada (y
    # se destilda clickeandola de nuevo). Es solo visual, para no perder de
    # vista las normas que estas revisando; no afecta filtros ni descargas.
    gob.configure_selection(selection_mode="multiple", use_checkbox=False,
                            rowMultiSelectWithClick=True)
    gob.configure_default_column(
        filter="agTextColumnFilter", sortable=True, resizable=True,
        floatingFilter=True, minWidth=120,
        suppressHeaderMenuButton=True, suppressMenu=True,
        filterParams={"filterOptions": ["contains"], "maxNumConditions": 1,
                      "caseSensitive": False, "textMatcher": matcher_sin_tilde,
                      "buttons": []},
        floatingFilterComponentParams={"suppressFilterButton": True})
    gob.configure_column("Fecha", width=110, minWidth=100)
    gob.configure_column("Descripción", flex=2, minWidth=240,
                         tooltipField="Descripción")
    # Etiquetas como badges Obelisco (chips). El filtro sigue trabajando sobre
    # el texto plano subyacente, el renderer solo cambia como se ve.
    gob.configure_column("Etiquetas", flex=1, minWidth=200, cellRenderer=JsCode("""
        class EtiquetasRenderer {
            init(p){
                this.e = document.createElement('div');
                (p.value || '').split(', ').filter(Boolean).forEach(t => {
                    var s = document.createElement('span');
                    s.innerText = t;
                    s.style.cssText = 'background:#ECF0F9;color:#2B59AD;'
                        + 'border-radius:999px;padding:1px 9px;'
                        + 'margin:1px 4px 1px 0;font-size:11px;font-weight:600;'
                        + 'display:inline-block;line-height:17px;';
                    this.e.appendChild(s);
                });
            }
            getGui(){ return this.e; }
        }"""))
    gob.configure_column("Normativa", minWidth=180)
    gob.configure_column("Organismo", minWidth=190)
    gob.configure_column("Score", type=["numericColumn"],
                         filter="agNumberColumnFilter",
                         filterParams={"maxNumConditions": 1, "buttons": []},
                         width=95, minWidth=90)
    gob.configure_column("Anexo", width=100, minWidth=90, filter=False,
                         sortable=False, cellRenderer=JsCode("""
        class AnexoRenderer {
            init(p){ this.e=document.createElement('span');
                if(p.value){ var a=document.createElement('a');
                    a.innerText='Ver ↗'; a.href=p.value; a.target='_blank';
                    a.style.color='#336ACC'; a.style.fontWeight='600';
                    a.style.textDecoration='none'; this.e.appendChild(a); }
                else { this.e.innerText='—'; this.e.style.color='#9EAAB8'; } }
            getGui(){ return this.e; }
        }"""))
    gob.configure_column("Boletín", width=110, minWidth=90)
    # Relevancia como chip con el semaforo unificado del monitor.
    colores_rel_js = json.dumps(mon.COLOR_RELEVANCIA)
    gob.configure_column("Relevancia", width=120, minWidth=110,
                         cellRenderer=JsCode(f"""
        class RelevanciaRenderer {{
            init(p){{
                const colores = {colores_rel_js};
                const col = colores[p.value] || '#69788A';
                this.e = document.createElement('span');
                this.e.innerText = p.value || '';
                this.e.style.cssText = 'background:' + col + '1A;color:' + col
                    + ';border-radius:999px;padding:2px 10px;font-size:11px;'
                    + 'font-weight:700;line-height:18px;display:inline-block;';
            }}
            getGui(){{ return this.e; }}
        }}"""))
    gob.configure_column("BOCBA", header_name="BOCBA", width=110, filter=False,
                         sortable=False, cellRenderer=JsCode("""
        class UrlRenderer {
            init(p){ this.e=document.createElement('a');
                this.e.innerText='Ver ↗'; this.e.href=p.value;
                this.e.target='_blank'; this.e.style.color='#336ACC';
                this.e.style.fontWeight='600'; this.e.style.textDecoration='none'; }
            getGui(){ return this.e; }
        }"""))
    grid_options = gob.build()
    # Carga Open Sans DENTRO del iframe del grid (no lo hereda de la pagina),
    # asi la fuente es identica en claro y oscuro y desde el primer render.
    grid_options["onGridReady"] = JsCode("""
        function(params){
          if(!document.getElementById('gf-opensans')){
            var l=document.createElement('link');
            l.id='gf-opensans'; l.rel='stylesheet';
            l.href='https://fonts.googleapis.com/css2?family=Open+Sans:'
                 + 'wght@400;600;700&display=swap';
            document.head.appendChild(l);
          }
        }""")
    grid_options["autoSizeStrategy"] = {"type": "fitGridWidth"}

    # El tema "streamlit" sigue el modo claro/oscuro en vivo (NO hardcodear
    # colores: eso traba la sincronizacion al cambiar de modo). Solo fijamos la
    # fuente (Open Sans, ya cargada arriba dentro del iframe).
    fuente = "'Open Sans', 'Segoe UI', Arial, sans-serif"
    grid_css = {
        ".ag-root-wrapper, .ag-cell, .ag-header-cell-label, .ag-header, "
        ".ag-input-field-input, input, .ag-paging-panel":
            {"font-family": f"{fuente} !important"},
        # Sombreado Obelisco para las filas seleccionadas (visible en claro
        # y oscuro).
        ".ag-row-selected":
            {"background-color": "rgba(51, 106, 204, 0.24) !important"},
    }

    # La key incluye el tema activo (para remontar el grid al cambiar claro/
    # oscuro) y el contador de "Reiniciar busqueda" (para limpiar los filtros
    # de columna, que viven dentro del iframe del grid).
    # NO_UPDATE: la seleccion de filas es puramente visual, no dispara
    # re-ejecuciones de la app (cada click seria una recarga si no).
    AgGrid(tabla, gridOptions=grid_options, theme="streamlit", height=560,
           allow_unsafe_jscode=True, custom_css=grid_css,
           update_mode=GridUpdateMode.NO_UPDATE,
           key=(f"grid_resultados_{st.context.theme.type}"
                f"_{st.session_state.get('grid_reset', 0)}"))

    # Contador + descargas: debajo del cuadro
    izq, c_csv, c_gace, c_inst = st.columns([1.3, 1, 1, 1])
    izq.caption(f"**{len(f)}** resultado(s)")
    # BOM utf-8-sig para que Excel abra bien las tildes con doble click.
    csv_bytes = tabla.to_csv(index=False).encode("utf-8-sig")
    c_csv.download_button("CSV (Excel)", icon=":material/download:",
                          data=csv_bytes, file_name="resultados_bocba.csv",
                          mime="text/csv", use_container_width=True)
    informe_f = informe_desde_df(f, ETIQUETAS, SIGLAS)
    pdf_bytes = generar_gacetilla_bytes(informe_f)
    c_gace.download_button("Gacetilla completa", icon=":material/download:",
                           data=pdf_bytes, file_name="gacetilla_bocba.pdf",
                           mime="application/pdf", use_container_width=True,
                           help="Todas las normas filtradas, agrupadas por "
                                "organismo (estilo Obelisco).")
    inst_bytes = generar_institucional_bytes(informe_f)
    c_inst.download_button("Edición institucional", icon=":material/download:",
                           data=inst_bytes,
                           file_name="gacetilla_institucional.pdf",
                           mime="application/pdf", use_container_width=True,
                           help="Solo las normas ALTA, en formato curado "
                                "listo para circular por mail.")

    # ---------------- GRAFICO: HALLAZGOS POR DIA ----------------
    with st.expander("Hallazgos por día", icon=":material/bar_chart:"):
        g = f[f["fecha_dt"].notna()]
        if g.empty:
            st.caption("Sin datos para graficar con los filtros actuales.")
        else:
            pivote = (g.pivot_table(index="fecha_dt", columns="relevancia",
                                    values="doc_id", aggfunc="count")
                        .reindex(columns=["ALTA", "MEDIA", "BAJA"])
                        .fillna(0).astype(int))
            st.caption("Documentos con coincidencias por día, según los "
                       "filtros aplicados.")
            # Semaforo unificado del monitor (gacetilla e informe PDF igual).
            st.bar_chart(pivote,
                         color=[mon.COLOR_RELEVANCIA[n]
                                for n in ("ALTA", "MEDIA", "BAJA")],
                         height=220)

    # ---------------- DETALLE DE MENCIONES ----------------
    with st.expander("Ver menciones de una norma",
                     icon=":material/manage_search:"):
        st.caption("Extractos del texto donde aparece cada término, con fuente "
                   "(norma o anexo) y página. El monitor guarda hasta 3 "
                   "menciones por fuente.")
        opciones = {}
        for idx, r in f.iterrows():
            clave = f"{r.cita} · {r.fecha}"
            if clave in opciones:   # misma cita y fecha: desambiguar por doc
                clave = f"{clave} (doc {r.doc_id})"
            opciones[clave] = idx
        sel = st.selectbox("Norma", list(opciones), index=None,
                           placeholder="Elegí una norma de los resultados…",
                           label_visibility="collapsed")
        if sel:
            row = f.loc[opciones[sel]]
            st.markdown(f"**{row['cita']}** · {row['organismo']} · "
                        f"{badge_rel(row['relevancia'])}",
                        unsafe_allow_html=True)
            if row["descripcion"]:
                st.caption(row["descripcion"])
            if row["url"]:
                st.markdown(f"[Ver en BOCBA ↗]({row['url']})")
            for kw, b in row["_kws"].items():
                menciones = b.get("cuerpo", []) + b.get("anexo", [])
                if not menciones:
                    continue
                label = LABEL_TILDE.get(mon.norm(kw), kw)
                st.markdown(f"**{label}** — {len(menciones)} mención(es):")
                for mcn in menciones:
                    st.markdown(f"> {mcn.get('ctx', '')}")

footer()
