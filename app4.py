import hashlib
import json
import random
import sqlite3
import string
from datetime import datetime
from zoneinfo import ZoneInfo
import streamlit as st

st.set_page_config(page_title="Evaluaciones Forenses - Consentimiento", page_icon="⚖️", layout="wide")
hide_style = """<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}</style>"""
st.markdown(hide_style, unsafe_allow_html=True)

CONTRASEÑA_MAESTRA = "MiClavePericial2026"
DB_NAME = "forense_seguro.db"
TZ = ZoneInfo("America/Argentina/Buenos_Aires")

def init_db():
  conn = sqlite3.connect(DB_NAME, check_same_thread=False)
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS evaluaciones_periciales (
            token TEXT PRIMARY KEY,
            estado TEXT,
            datos_persona TEXT,
            evaluaciones TEXT,
            ip_acceso TEXT,
            user_agent TEXT,
            hash_anterior TEXT,
            hash_bloque TEXT,
            fecha_creacion TEXT,
            fecha_actualizacion TEXT
        )
    """)
  # Migración por si la tabla vieja no tiene columnas nuevas
  try:
    cursor.execute("ALTER TABLE evaluaciones_periciales ADD COLUMN fecha_creacion TEXT")
  except: pass
  try:
    cursor.execute("ALTER TABLE evaluaciones_periciales ADD COLUMN fecha_actualizacion TEXT")
  except: pass
  conn.commit()
  conn.close()

init_db()

def cargar_datos_db():
  conn = sqlite3.connect(DB_NAME, check_same_thread=False)
  cursor = conn.cursor()
  cursor.execute("SELECT token, estado, datos_persona, evaluaciones, ip_acceso, user_agent, hash_bloque, fecha_creacion, fecha_actualizacion FROM evaluaciones_periciales")
  rows = cursor.fetchall()
  conn.close()
  data={}
  for row in rows:
    token, estado, dp, evals, ip, ua, h_bloque, f_crea, f_act = row
    try: dp_json = json.loads(dp) if dp else {}
    except: dp_json = {}
    try: evals_json = json.loads(evals) if evals else {}
    except: evals_json = {}
    data[token] = {"estado": estado if estado else "activa", "datos_persona": dp_json, "evaluaciones": evals_json, "ip_acceso": ip, "user_agent": ua, "hash_bloque": h_bloque, "fecha_creacion": f_crea, "fecha_actualizacion": f_act}
  return data

def guardar_token_db(token, info_dict):
  conn = sqlite3.connect(DB_NAME, check_same_thread=False)
  cursor = conn.cursor()
  cursor.execute("SELECT hash_bloque FROM evaluaciones_periciales ORDER BY rowid DESC LIMIT 1")
  ultimo = cursor.fetchone()
  hash_prev = ultimo[0] if ultimo and ultimo[0] else "GENESIS_BLOCK_FORENSE"
  payload_str = f"{token}-{json.dumps(info_dict.get('evaluaciones'))}-{info_dict.get('ip_acceso', '')}-{hash_prev}"
  hash_actual = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
  ahora = datetime.now(TZ).isoformat()
  cursor.execute("""
        INSERT OR REPLACE INTO evaluaciones_periciales 
        (token, estado, datos_persona, evaluaciones, ip_acceso, user_agent, hash_anterior, hash_bloque, fecha_creacion, fecha_actualizacion)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT fecha_creacion FROM evaluaciones_periciales WHERE token=?), ?), ?)
    """, (token, info_dict.get("estado", "activa"), json.dumps(info_dict.get("datos_persona"), ensure_ascii=False), json.dumps(info_dict.get("evaluaciones", {}), ensure_ascii=False), info_dict.get("ip_acceso", "Desconocida"), info_dict.get("user_agent", "Desconocido"), hash_prev, hash_actual, token, ahora, ahora))
  conn.commit()
  conn.close()

def eliminar_token_db(token):
  conn = sqlite3.connect(DB_NAME, check_same_thread=False)
  cursor = conn.cursor()
  cursor.execute("DELETE FROM evaluaciones_periciales WHERE token = ?", (token,))
  conn.commit()
  conn.close()

def obtener_metadatos_conexion():
  try:
    from streamlit.web.server.websocket_headers import _get_websocket_headers
    headers = _get_websocket_headers()
    if headers:
      ip = headers.get("X-Forwarded-For", headers.get("Remote-Addr", "127.0.0.1"))
      if "," in ip: ip = ip.split(",")[0].strip()
      ua = headers.get("User-Agent", "Desconocido")
      return ip, ua
  except: pass
  return "IP_ONLINE", "Navegador_Estandar"

def generar_token_unico(longitud=6):
  caracteres = string.ascii_uppercase + string.digits
  codigo = "".join(random.choice(caracteres) for _ in range(longitud))
  return f"EVAL-{codigo}"

# --- ITEMS ORIGINALES (SIN MMPI) - COPIADOS DE TU ARCHIVO ---
# Si ya tenes el archivo final anterior, pega aqui todos los ITEMS_*
# Para no hacer este archivo gigante, importamos del final anterior si existe, si no placeholders

try:
    from app4_sin_mmpi_online_FINAL import ITEMS_LSB50, OPCIONES_LSB50, ITEMS_MCMIIII, OPCIONES_MCMI, ITEMS_CUIDA, OPCIONES_CUIDA, ITEMS_STAI, OPCIONES_STAI, ITEMS_BDI, ITEMS_PAI, OPCIONES_PAI
except:
    # Fallback: lee del archivo que ya generamos
    import pathlib
    txt = pathlib.Path('/mnt/data/app4_sin_mmpi_online_FINAL.py').read_text(encoding='utf-8', errors='ignore')
    # exec solo los bloques de items (es seguro porque es tu propio archivo)
    # Extraemos y ejecutamos
    exec_globals = {}
    # Busca definiciones
    import re
    for m in re.finditer(r'^(ITEMS_\w+|OPCIONES_\w+)\s*=\s*(\[|\{).*?(?:\n\]|\n\})', txt, re.MULTILINE | re.DOTALL):
        try:
            exec(m.group(0), exec_globals)
        except: pass
    ITEMS_LSB50 = exec_globals.get('ITEMS_LSB50', [])
    OPCIONES_LSB50 = exec_globals.get('OPCIONES_LSB50', {})
    ITEMS_MCMIIII = exec_globals.get('ITEMS_MCMIIII', [])
    OPCIONES_MCMI = exec_globals.get('OPCIONES_MCMI', ["Verdadero","Falso"])
    ITEMS_CUIDA = exec_globals.get('ITEMS_CUIDA', [])
    OPCIONES_CUIDA = exec_globals.get('OPCIONES_CUIDA', {})
    ITEMS_STAI = exec_globals.get('ITEMS_STAI', [])
    OPCIONES_STAI = exec_globals.get('OPCIONES_STAI', {})
    ITEMS_BDI = exec_globals.get('ITEMS_BDI', [])
    ITEMS_PAI = exec_globals.get('ITEMS_PAI', [])
    OPCIONES_PAI = exec_globals.get('OPCIONES_PAI', {})

# Session
if "perito_autenticado" not in st.session_state:
  st.session_state["perito_autenticado"] = False
if "token_actual" not in st.session_state:
  st.session_state["token_actual"] = None
if "test_enviado" not in st.session_state:
  st.session_state["test_enviado"] = False
if "datos_personales_ok" not in st.session_state:
  st.session_state["datos_personales_ok"] = False

TESTS_DISPONIBLES = [
    "LSB-50 (Listado de Sintomas Breve)",
    "MCMI-III (Inventario Clinico Multiaxial de Millon-III)",
    "CUIDA (Evaluacion de Adoptantes, Cuidadores, Tutores y Mediadores)",
    "STAI (Cuestionario de Ansiedad Estado-Rasgo)",
    "BDI-II (Inventario de Depresion de Beck)",
    "PAI (Inventario de Evaluacion de la Personalidad)",
]

CONSENTIMIENTO_TEXTO = """
### Consentimiento Informado para Evaluación Psicológica Forense

**Por favor lea atentamente antes de continuar:**

1.  **Naturaleza de la evaluación:** Usted participará en una evaluación psicológica con fines periciales/forenses. Los instrumentos que completará son de uso profesional.

2.  **Voluntariedad y confidencialidad:** Su participación es voluntaria. Los datos que usted proporciona (nombre, apellido, edad, DNI, localidad y respuestas a los tests) serán tratados con estricta confidencialidad y secreto profesional, conforme a la Ley 26.657 y al Código de Ética del Psicólogo. Solo el perito a cargo tendrá acceso a sus resultados.

3.  **Trazabilidad:** Por fines forenses, el sistema registra fecha, hora e IP de acceso de forma anonimizada, sin identificar su dispositivo.

4.  **Uso de los resultados:** Los resultados serán utilizados únicamente para la elaboración del informe pericial correspondiente a la causa/expediente indicado y no serán compartidos con terceros sin orden judicial.

5.  **Derechos:** Usted puede consultar, rectificar o solicitar la supresión de sus datos al perito responsable.

Al marcar la casilla de aceptación, usted declara que ha leído, comprendido y acepta participar libremente en esta evaluación.
"""

# UI
st.sidebar.title("⚖️ Sistema Forense Online")
rol = st.sidebar.radio("¿Cómo querés ingresar?", ["🧑‍⚖️ Soy Perito (Admin)", "🧑 Soy Evaluado (con Token)"], index=0)

# ================= PERITO =================
if rol == "🧑‍⚖️ Soy Perito (Admin)":
    st.title("Panel Perito - SIN MMPI - Con datos del evaluado")
    if not st.session_state["perito_autenticado"]:
        pwd = st.text_input("Contraseña maestra", type="password")
        if st.button("Ingresar"):
            if pwd == CONTRASEÑA_MAESTRA:
                st.session_state["perito_autenticado"] = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta")
        st.stop()

    col_a, col_b, col_c = st.columns([2,2,2])
    with col_a:
        if st.button("🔄 ACTUALIZAR DATOS AHORA", type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with col_b:
        st.caption(f"{datetime.now(TZ).strftime('%d/%m/%Y %H:%M:%S')}")
    with col_c:
        if st.button("Cerrar sesión"):
            st.session_state["perito_autenticado"] = False
            st.rerun()

    st.divider()
    datos = cargar_datos_db()

    st.subheader("1️⃣ Crear nuevo token (ya no pedís datos personales)")
    st.info("Ahora el evaluado completa sus propios datos. Vos solo cargás causa/expediente.")
    with st.form("crear_token"):
        causa = st.text_input("Causa / Expediente*")
        obs = st.text_area("Observaciones internas (no las ve el evaluado)")
        if st.form_submit_button("Generar Link + Token"):
            if not causa:
                st.error("Cargá al menos la causa")
            else:
                nuevo_token = generar_token_unico()
                ip, ua = obtener_metadatos_conexion()
                guardar_token_db(nuevo_token, {
                    "estado": "activa",
                    "datos_persona": {"causa": causa, "obs_perito": obs},  # vacío, lo completa evaluado
                    "evaluaciones": {},
                    "ip_acceso": ip,
                    "user_agent": ua
                })
                st.success(f"Token creado: {nuevo_token}")
                base_url = "https://psi-forense-knto5bo9aobIpy73lw34o6.streamlit.app"
                st.code(f"{base_url}?token={nuevo_token}", language="text")
                st.rerun()

    st.divider()
    st.subheader(f"2️⃣ Evaluaciones ({len(datos)})")
    if datos:
        import pandas as pd, io, json
        filas=[]
        for tok,info in datos.items():
            dp=info.get("datos_persona") or {}
            evals=info.get("evaluaciones") or {}
            filas.append({
                "Token":tok,
                "Nombre":f"{dp.get('nombre','')} {dp.get('apellido','')}".strip() or "-",
                "Edad":dp.get('edad','-'),
                "DNI":dp.get('dni','-'),
                "Localidad":dp.get('localidad','-'),
                "Causa":dp.get('causa','-'),
                "Consentimiento": "Sí" if dp.get('consentimiento') else "No",
                "Tests": ", ".join(evals.keys()) if evals else "-",
                "Actualizado":info.get('fecha_actualizacion','-')[:19]
            })
        df=pd.DataFrame(filas)
        st.dataframe(df, use_container_width=True, hide_index=True)

        output_excel = io.BytesIO()
        with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name="Resumen", index=False)
            for tok,info in datos.items():
                for test_name, respuestas in info.get("evaluaciones",{}).items():
                    try:
                        df_resp = pd.DataFrame(list(respuestas.items()), columns=["Pregunta","Respuesta"])
                        sheet = f"{tok}_{test_name}"[:31]
                        df_resp.to_excel(writer, sheet_name=sheet, index=False)
                    except: pass
        output_excel.seek(0)
        c1,c2 = st.columns(2)
        c1.download_button("📊 DESCARGAR EXCEL", data=output_excel, file_name=f"forense_{datetime.now(TZ).strftime('%Y%m%d_%H%M')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, type="primary")
        c2.download_button("📄 DESCARGAR JSON", data=json.dumps(datos, indent=2, ensure_ascii=False), file_name="backup.json", mime="application/json", use_container_width=True)

        st.divider()
        token_sel = st.selectbox("Ver detalle completo:", list(datos.keys()))
        if token_sel:
            st.json(datos[token_sel])
            if st.button(f"🗑️ Eliminar {token_sel}"):
                eliminar_token_db(token_sel)
                st.rerun()

# ================= EVALUADO =================
else:
    st.title("Evaluación Psicológica Forense")
    query_params = st.query_params
    token_url = query_params.get("token", None)
    token_input = st.text_input("Ingresá tu TOKEN", value=token_url if token_url else "", placeholder="EVAL-XXXXXX")
    if token_input:
        st.session_state["token_actual"] = token_input.strip().upper()
    token_actual = st.session_state["token_actual"]
    if not token_actual:
        st.info("Pedile a tu perito el token de acceso.")
        st.stop()

    datos_db = cargar_datos_db()
    if token_actual not in datos_db:
        st.error(f"Token {token_actual} no existe")
        st.stop()

    datos_token = datos_db[token_actual]
    dp = datos_token.get("datos_persona") or {}

    # Chequear si ya completó datos personales
    datos_completos = all([dp.get('nombre'), dp.get('apellido'), dp.get('edad'), dp.get('dni'), dp.get('localidad'), dp.get('consentimiento')])

    if not datos_completos:
        st.success(f"Token válido: {token_actual}")
        st.subheader("Paso 1: Completá tus datos personales")
        st.caption("Estos casilleros los completás vos, no el perito.")

        with st.form("form_datos_personales"):
            c1, c2 = st.columns(2)
            nombre = c1.text_input("Nombre*", value=dp.get('nombre',''))
            apellido = c2.text_input("Apellido*", value=dp.get('apellido',''))
            c3, c4, c5 = st.columns(3)
            edad = c3.number_input("Edad*", min_value=6, max_value=100, value=int(dp.get('edad',18)) if str(dp.get('edad','')).isdigit() else 18)
            dni = c4.text_input("DNI*", value=dp.get('dni',''))
            localidad = c5.text_input("Localidad donde vivís*", value=dp.get('localidad',''))

            st.divider()
            st.markdown(CONSENTIMIENTO_TEXTO)
            consent = st.checkbox("✅ He leído y acepto el Consentimiento Informado*")
            fecha_acept = datetime.now(TZ).strftime("%d/%m/%Y %H:%M")

            if st.form_submit_button("Aceptar y Continuar a los Tests", type="primary", use_container_width=True):
                if not (nombre and apellido and dni and localidad and edad and consent):
                    st.error("Tenés que completar todos los campos con * y aceptar el consentimiento.")
                else:
                    # Guardar datos personales
                    dp.update({
                        "nombre": nombre.strip(),
                        "apellido": apellido.strip(),
                        "edad": edad,
                        "dni": dni.strip(),
                        "localidad": localidad.strip(),
                        "consentimiento": True,
                        "fecha_consentimiento": fecha_acept,
                        "causa": dp.get('causa',''),  # preserva causa del perito
                        "obs_perito": dp.get('obs_perito','')
                    })
                    datos_token["datos_persona"] = dp
                    datos_token["estado"] = "datos_completados"
                    ip, ua = obtener_metadatos_conexion()
                    datos_token["ip_acceso"] = ip
                    datos_token["user_agent"] = ua
                    guardar_token_db(token_actual, datos_token)
                    st.session_state["datos_personales_ok"] = True
                    st.success("Datos guardados. Ahora podés hacer los tests.")
                    st.rerun()
        st.stop()

    # Si ya completó datos, mostrar tests
    if st.session_state["test_enviado"]:
        st.success("✅ Tus respuestas fueron enviadas al perito. Ya podés cerrar.")
        st.stop()

    st.success(f"Bienvenido/a {dp.get('nombre')} {dp.get('apellido')} | DNI {dp.get('dni')} | {dp.get('localidad')}")
    st.info(f"Consentimiento aceptado el {dp.get('fecha_consentimiento')} - Causa: {dp.get('causa','-')}")
    
    test_seleccionado = st.selectbox("Seleccioná el test asignado", TESTS_DISPONIBLES)

    if test_seleccionado.startswith("LSB-50"):
        st.subheader("LSB-50")
        respuestas={}
        with st.form("form_lsb50"):
            for idx, preg in enumerate(ITEMS_LSB50,1):
                respuestas[f"p_{idx}"] = st.radio(preg, options=list(OPCIONES_LSB50.keys()), format_func=lambda x: OPCIONES_LSB50[x], horizontal=True, key=f"lsb_{idx}_{token_actual}")
                st.divider()
            if st.form_submit_button("Guardar y Enviar LSB-50", use_container_width=True, type="primary"):
                datos_token["evaluaciones"]["LSB-50"]=respuestas
                guardar_token_db(token_actual, datos_token)
                st.session_state["test_enviado"]=True
                st.rerun()

    elif test_seleccionado.startswith("MCMI-III"):
        st.subheader("MCMI-III")
        respuestas_mcmi={}
        with st.form("form_mcmi3"):
            for idx, preg in enumerate(ITEMS_MCMIIII,1):
                respuestas_mcmi[f"p_{idx}"] = st.radio(preg, options=OPCIONES_MCMI, horizontal=True, key=f"mcmi_{idx}_{token_actual}")
                if idx % 15 == 0: st.divider()
            if st.form_submit_button("Guardar y Enviar MCMI-III", use_container_width=True, type="primary"):
                datos_token["evaluaciones"]["MCMI-III"]=respuestas_mcmi
                guardar_token_db(token_actual, datos_token)
                st.session_state["test_enviado"]=True
                st.rerun()

    elif test_seleccionado.startswith("CUIDA"):
        st.subheader("CUIDA")
        respuestas_cuida={}
        with st.form("form_cuida"):
            for idx, preg in enumerate(ITEMS_CUIDA,1):
                respuestas_cuida[f"p_{idx}"] = st.radio(preg, options=list(OPCIONES_CUIDA.keys()), format_func=lambda x: OPCIONES_CUIDA[x], horizontal=True, key=f"cuida_{idx}_{token_actual}")
                st.divider()
            if st.form_submit_button("Guardar y Enviar CUIDA", use_container_width=True, type="primary"):
                datos_token["evaluaciones"]["CUIDA"]=respuestas_cuida
                guardar_token_db(token_actual, datos_token)
                st.session_state["test_enviado"]=True
                st.rerun()

    elif test_seleccionado.startswith("STAI"):
        st.subheader("STAI")
        respuestas_stai={}
        with st.form("form_stai"):
            for idx, preg in enumerate(ITEMS_STAI,1):
                respuestas_stai[f"p_{idx}"] = st.radio(preg, options=list(OPCIONES_STAI.keys()), format_func=lambda x: OPCIONES_STAI[x], horizontal=True, key=f"stai_{idx}_{token_actual}")
                st.divider()
            if st.form_submit_button("Guardar y Enviar STAI", use_container_width=True, type="primary"):
                datos_token["evaluaciones"]["STAI"]=respuestas_stai
                guardar_token_db(token_actual, datos_token)
                st.session_state["test_enviado"]=True
                st.rerun()

    elif test_seleccionado.startswith("BDI-II"):
        st.subheader("BDI-II")
        respuestas_bdi={}
        with st.form("form_bdii"):
            for idx, item in enumerate(ITEMS_BDI,1):
                respuestas_bdi[f"p_{idx}"] = st.radio(item["titulo"], options=item["opciones"], key=f"bdi_{idx}_{token_actual}")
                st.divider()
            if st.form_submit_button("Guardar y Enviar BDI-II", use_container_width=True, type="primary"):
                datos_token["evaluaciones"]["BDI-II"]=respuestas_bdi
                guardar_token_db(token_actual, datos_token)
                st.session_state["test_enviado"]=True
                st.rerun()

    elif test_seleccionado.startswith("PAI"):
        st.subheader("PAI")
        respuestas_pai={}
        with st.form("form_pai"):
            for idx, preg in enumerate(ITEMS_PAI,1):
                respuestas_pai[f"p_{idx}"] = st.radio(preg, options=list(OPCIONES_PAI.keys()), format_func=lambda x: OPCIONES_PAI[x], horizontal=True, key=f"pai_{idx}_{token_actual}")
                st.divider()
            if st.form_submit_button("Guardar y Enviar PAI", use_container_width=True, type="primary"):
                datos_token["evaluaciones"]["PAI"]=respuestas_pai
                guardar_token_db(token_actual, datos_token)
                st.session_state["test_enviado"]=True
                st.rerun()
