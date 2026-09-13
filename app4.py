import hashlib
import json
import random
import sqlite3
import string
import io
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st

# -----------------------------------------------------------------------------
# CONFIGURACIÓN
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Evaluaciones Psicológicas Forenses - ONLINE", page_icon="⚖️", layout="wide")
hide_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
div[data-testid="stStatusWidget"] {visibility: hidden;}
</style>
"""
st.markdown(hide_style, unsafe_allow_html=True)

CONTRASEÑA_MAESTRA = "MiClavePericial2026"
DB_NAME = "forense_seguro.db"
TZ = ZoneInfo("America/Argentina/Buenos_Aires")

# -----------------------------------------------------------------------------
# DB - CON CACHE PARA MODO ONLINE
# -----------------------------------------------------------------------------
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
    conn.commit()
    conn.close()

init_db()

def cargar_datos_db(force_reload=False):
    # force_reload ignora caché de streamlit
    if force_reload:
        st.cache_data.clear()
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT token, estado, datos_persona, evaluaciones, ip_acceso, user_agent, hash_bloque, fecha_creacion, fecha_actualizacion FROM evaluaciones_periciales")
    rows = cursor.fetchall()
    conn.close()
    data = {}
    for row in rows:
        token, estado, dp, evals, ip, ua, h_bloque, f_crea, f_act = row
        try: dp_json = json.loads(dp) if dp else None
        except: dp_json = {"raw": dp}
        try: evals_json = json.loads(evals) if evals else {}
        except: evals_json = {}
        data[token] = {
            "estado": estado if estado else "activa",
            "datos_persona": dp_json,
            "evaluaciones": evals_json,
            "ip_acceso": ip,
            "user_agent": ua,
            "hash_bloque": h_bloque,
            "fecha_creacion": f_crea,
            "fecha_actualizacion": f_act,
        }
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
    """, (
        token,
        info_dict.get("estado", "activa"),
        json.dumps(info_dict.get("datos_persona"), ensure_ascii=False),
        json.dumps(info_dict.get("evaluaciones", {}), ensure_ascii=False),
        info_dict.get("ip_acceso", "Desconocida"),
        info_dict.get("user_agent", "Desconocido"),
        hash_prev,
        hash_actual,
        token, ahora,
        ahora
    ))
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

# -----------------------------------------------------------------------------
# IMPORTAR TUS BANCOS DE ITEMS (los dejo con placeholders si no los pegas)
# -----------------------------------------------------------------------------
# Para no hacer el archivo gigante, importamos desde tu archivo original si existe
# Si no, define al menos MCMI-III
try:
    # intenta importar del archivo original si lo subiste como modulo
    import importlib.util, sys, pathlib
    # Si pegaste los ITEMS aqui, se usaran esos.
    ITEMS_MCMIIII
except:
    # PLACEHOLDER MCMI-III - reemplaza con tu lista completa
    ITEMS_MCMIIII = [f"Ítem MCMI-III {i+1}" for i in range(175)]
    OPCIONES_MCMI = ["Verdadero", "Falso"]

# Si tenes los otros tests, descomenta el import de tu archivo original:
# from code_10_mcmi_iii_ok import ITEMS_LSB50, ITEMS_MMPI2RF, ITEMS_CUIDA, etc.

# -----------------------------------------------------------------------------
# LOGICA DE ROLES
# -----------------------------------------------------------------------------
if "perito_autenticado" not in st.session_state:
    st.session_state["perito_autenticado"] = False
if "token_actual" not in st.session_state:
    st.session_state["token_actual"] = None
if "test_enviado" not in st.session_state:
    st.session_state["test_enviado"] = False

# SIDEBAR - SELECTOR DE ROL
st.sidebar.title("⚖️ Sistema Forense Online")
rol = st.sidebar.radio("¿Cómo querés ingresar?", ["🧑‍⚖️ Soy Perito (Admin)", "🧑 Soy Evaluado (con Token)"], index=0)

# =============================================================================
# ROL 1: PERITO
# =============================================================================
if rol == "🧑‍⚖️ Soy Perito (Admin)":
    st.title("Panel Perito - Control Central Online")

    if not st.session_state["perito_autenticado"]:
        pwd = st.text_input("Contraseña maestra", type="password")
        if st.button("Ingresar"):
            if pwd == CONTRASEÑA_MAESTRA:
                st.session_state["perito_autenticado"] = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta")
        st.stop()

    # --- BARRA DE ACCION PRINCIPAL ---
    col_a, col_b, col_c = st.columns([2,2,2])
    with col_a:
        if st.button("🔄 ACTUALIZAR DATOS AHORA", type="primary", use_container_width=True, help="Trae todos los resultados que cargaron desde la otra ciudad"):
            st.cache_data.clear()
            st.toast("Datos actualizados desde la nube!", icon="✅")
            st.rerun()
    with col_b:
        st.caption(f"Última actualización: {datetime.now(TZ).strftime('%d/%m/%Y %H:%M:%S')}")
    with col_c:
        if st.button("Cerrar sesión perito"):
            st.session_state["perito_autenticado"] = False
            st.rerun()

    st.divider()

    # Cargar datos (siempre fresco al entrar)
    datos = cargar_datos_db(force_reload=False)

    # CREAR NUEVO TOKEN
    st.subheader("1️⃣ Crear nuevo evaluado")
    with st.form("crear_token"):
        c1, c2, c3 = st.columns(3)
        nombre = c1.text_input("Nombre y apellido del evaluado*")
        dni = c2.text_input("DNI")
        causa = c3.text_input("Causa / Expediente")
        obs = st.text_area("Observaciones")
        if st.form_submit_button("Generar Link + Token"):
            nuevo_token = generar_token_unico()
            ip, ua = obtener_metadatos_conexion()
            guardar_token_db(nuevo_token, {
                "estado": "activa",
                "datos_persona": {"nombre": nombre, "dni": dni, "causa": causa, "obs": obs},
                "evaluaciones": {},
                "ip_acceso": ip,
                "user_agent": ua
            })
            st.success(f"Token creado: **{nuevo_token}**")
            st.info(f"Pasale a la otra persona este link: \n\n `{st.secrets.get('app_url','https://tu-app.streamlit.app')}?token={nuevo_token}` \n\nO solo el token: {nuevo_token}")
            st.rerun()

    st.divider()
    st.subheader(f"2️⃣ Evaluaciones en curso ({len(datos)})")

    if not datos:
        st.warning("No hay evaluaciones todavía. Creá un token arriba.")
    else:
        # Tabla resumen
        filas = []
        for tok, info in datos.items():
            dp = info.get("datos_persona") or {}
            evals = info.get("evaluaciones") or {}
            filas.append({
                "Token": tok,
                "Nombre": dp.get("nombre","-"),
                "DNI": dp.get("dni","-"),
                "Estado": info.get("estado"),
                "Tests completados": ", ".join(evals.keys()) if evals else "-",
                "Actualizado": info.get("fecha_actualizacion","-"),
                "IP": info.get("ip_acceso")
            })
        df = pd.DataFrame(filas)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # DESCARGA MASIVA - ESTO ES LO QUE PEDISTE
        st.markdown("### 3️⃣ 📥 Descargar resultados al Actualizar")
        st.caption("Cuando apretás ACTUALIZAR arriba, acá se generan los archivos con lo que cargó la otra persona en la otra ciudad.")

        # Preparar Excel
        output_excel = io.BytesIO()
        with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name="Resumen", index=False)
            # Una hoja por cada evaluado con sus respuestas
            for tok, info in datos.items():
                evals = info.get("evaluaciones", {})
                for test_name, respuestas in evals.items():
                    try:
                        df_resp = pd.DataFrame(list(respuestas.items()), columns=["Pregunta","Respuesta"])
                        sheet = f"{tok}_{test_name}"[:31]
                        df_resp.to_excel(writer, sheet_name=sheet, index=False)
                    except: pass
        output_excel.seek(0)

        c1, c2 = st.columns(2)
        c1.download_button("📊 DESCARGAR EXCEL COMPLETO (Todo)", data=output_excel, file_name=f"forense_resultados_{datetime.now(TZ).strftime('%Y%m%d_%H%M')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, type="primary")
        
        json_data = json.dumps(datos, indent=2, ensure_ascii=False)
        c2.download_button("📄 DESCARGAR JSON (Backup forense)", data=json_data, file_name=f"forense_backup_{datetime.now(TZ).strftime('%Y%m%d_%H%M')}.json", mime="application/json", use_container_width=True)

        st.divider()
        # Detalle por token
        token_sel = st.selectbox("Ver detalle de:", list(datos.keys()))
        if token_sel:
            st.json(datos[token_sel])
            if st.button(f"🗑️ Eliminar {token_sel}", type="secondary"):
                eliminar_token_db(token_sel)
                st.rerun()

# =============================================================================
# ROL 2: EVALUADO
# =============================================================================
else:
    st.title("Evaluación Psicológica - Acceso Evaluado")
    
    # Si viene con ?token=EVAL-XXXX en la URL
    query_params = st.query_params
    token_url = query_params.get("token", None)

    token_input = st.text_input("Ingresá tu TOKEN de evaluación", value=token_url if token_url else "", placeholder="EVAL-XXXXXX")
    
    if token_input:
        st.session_state["token_actual"] = token_input.strip().upper()
    
    token_actual = st.session_state["token_actual"]

    if not token_actual:
        st.info("Pedile a tu perito el token. Ej: EVAL-A1B2C3")
        st.stop()

    datos_db = cargar_datos_db()
    if token_actual not in datos_db:
        st.error(f"Token {token_actual} no existe o fue eliminado. Verificá que esté bien escrito.")
        st.stop()

    datos_token = datos_db[token_actual]
    
    if st.session_state["test_enviado"]:
        st.success("✅ Tus respuestas fueron enviadas correctamente al perito. Ya podés cerrar esta ventana.")
        st.info("El perito verá tus resultados cuando apriete ACTUALIZAR en su panel.")
        if st.button("Hacer otro test"):
            st.session_state["test_enviado"] = False
            st.rerun()
        st.stop()

    st.success(f"Token válido: {token_actual} | Evaluado: {datos_token['datos_persona'].get('nombre','-')}")
    
    # --- FORMULARIO DE TESTS (EJEMPLO MCMI-III) ---
    test_seleccionado = st.selectbox("Seleccioná el test asignado", ["MCMI-III (Inventario Clínico Multiaxial de Millon-III)"])

    if test_seleccionado.startswith("MCMI-III"):
        st.subheader("MCMI-III")
        st.info("Responda Verdadero o Falso según se aplique a usted. Al finalizar, sus datos se enviarán automáticamente al perito en la otra ciudad.")
        respuestas_mcmi = {}
        with st.form("form_mcmi3_online"):
            for idx, preg in enumerate(ITEMS_MCMIIII, 1):
                # Si tu lista original es larga, esto renderiza todo
                label = preg if isinstance(preg, str) else str(preg)
                respuestas_mcmi[f"p_{idx}"] = st.radio(label, options=["Verdadero","Falso"], horizontal=True, key=f"mcmi_{idx}_{token_actual}")
                if idx % 10 == 0:
                    st.divider()
            if st.form_submit_button("✅ Guardar y Enviar al Perito", use_container_width=True, type="primary"):
                datos_token["evaluaciones"]["MCMI-III"] = respuestas_mcmi
                datos_token["estado"] = "completado"
                ip, ua = obtener_metadatos_conexion()
                datos_token["ip_acceso"] = ip
                datos_token["user_agent"] = ua
                guardar_token_db(token_actual, datos_token)
                st.session_state["test_enviado"] = True
                st.rerun()
