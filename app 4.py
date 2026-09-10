import hashlib
import json
import random
import sqlite3
import string
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import streamlit as st

# Configuración general de la página
st.set_page_config(
    page_title="Evaluaciones Psicológicas Forenses",
    page_icon="⚖️",
    layout="centered",
)

# -----------------------------------------------------------------------------
# OCULTAR MENÚ, FOOTER Y CABECERA DE STREAMLIT
# -----------------------------------------------------------------------------
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN Y BASE DE DATOS SQLITE SEGURA (TRAZABILIDAD FORENSE)
# -----------------------------------------------------------------------------
CONTRASEÑA_MAESTRA = "MiClavePericial2026"
DB_NAME = "forense_seguro.db"


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
            hash_bloque TEXT
        )
    """)
    conn.commit()
    conn.close()


init_db()


def cargar_datos_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT token, estado, datos_persona, evaluaciones, ip_acceso,"
        " user_agent, hash_bloque FROM evaluaciones_periciales"
    )
    rows = cursor.fetchall()
    conn.close()

    data = {}
    for row in rows:
        token, estado, dp, evals, ip, ua, h_bloque = row
        data[token] = {
            "estado": estado if estado else "activa",
            "datos_persona": json.loads(dp) if dp else None,
            "evaluaciones": json.loads(evals) if evals else {},
            "ip_acceso": ip,
            "user_agent": ua,
            "hash_bloque": h_bloque,
        }
    return data


def guardar_token_db(token, info_dict):
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT hash_bloque FROM evaluaciones_periciales ORDER BY rowid DESC LIMIT 1"
    )
    ultimo = cursor.fetchone()
    hash_prev = ultimo[0] if ultimo and ultimo[0] else "GENESIS_BLOCK_FORENSE"

    payload_str = (
        f"{token}-{json.dumps(info_dict.get('evaluaciones'))}-{info_dict.get('ip_acceso', '')}-{hash_prev}"
    )
    hash_actual = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

    cursor.execute(
        """
        INSERT OR REPLACE INTO evaluaciones_periciales 
        (token, estado, datos_persona, evaluaciones, ip_acceso, user_agent, hash_anterior, hash_bloque)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            token,
            info_dict.get("estado", "activa"),
            json.dumps(info_dict.get("datos_persona")),
            json.dumps(info_dict.get("evaluaciones", {})),
            info_dict.get("ip_acceso", "Desconocida"),
            info_dict.get("user_agent", "Desconocido"),
            hash_prev,
            hash_actual,
        ),
    )
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
            if "," in ip:
                ip = ip.split(",")[0].strip()
            ua = headers.get("User-Agent", "Desconocido")
            return ip, ua
    except Exception:
        pass
    return "IP_LOCAL_O_NO_DETECTADA", "Navegador_Estandar"


claves_globales = cargar_datos_db()

if "perito_autenticado" not in st.session_state:
    st.session_state["perito_autenticado"] = False


def generar_token_unico(longitud=6):
    caracteres = string.ascii_uppercase + string.digits
    codigo = "".join(random.choice(caracteres) for _ in range(longitud))
    return f"EVAL-{codigo}"


# -----------------------------------------------------------------------------
# 2. BANCO COMPLETO DE REACTIVOS DE LAS PRUEBAS
# -----------------------------------------------------------------------------
ITEMS_LSB50 = [
    "1. Mi corazón palpita o va muy deprisa.",
    "2. Me siento triste.",
    "3. Tengo ganas de romper o destruir algo.",
    "4. Siento nerviosismo o agitación interior.",
    "5. Tengo mareos o sensaciones de desmayo.",
    "6. Me preocupa la dejadez y el descuido.",
    "7. Tengo que comprobar una y otra vez todo lo que hago.",
    "8. Me cuesta tomar decisiones.",
    "9. Me irrito o enfado por cualquier cosa.",
    "10. Siento miedo en la calle o en espacios abiertos.",
    "11. Tengo dolores de cabeza.",
    "12. Me siento decaído o falto de fuerzas.",
    "13. Me despierto por la madrugada.",
    "14. Duermo inquieto o me despierto mucho por la noche.",
    "15. Doy vueltas a palabras o ideas que no consigo quitarme de la cabeza.",
    "16. Me siento incomodo o vergonzoso cuando estoy en reuniones o con gente.",
    "17. Me vienen ideas de acabar con mi vida.",
    "18. Tengo miedo sin motivo.",
    "19. Tengo molestias digestivas o náuseas.",
    "20. Siento hormigueo o se me duerme alguna parte de mi cuerpo.",
    "21. Veo mi futuro sin esperanza.",
    "22. Me da miedo estar solo.",
    "23. Tengo ataques de ira que no puedo controlar.",
    "24. Me siento incomprendido o no me hacen caso.",
    "25. Me da miedo salir de casa sólo.",
    "26. Me parece que otras personas me observan o hablan de mí.",
    "27. Me cuesta dormirme.",
    "28. Tengo sentimiento de culpa.",
    "29. Me siento incómodo comiendo o bebiendo en público.",
    "30. Me siento herido con facilidad.",
    "31. Me siento incapaz de hacer las cosas o terminar las tareas.",
    "32. No siento interés por nada.",
    "33. Tengo manías como repetir cosas innecesariamente (tocar algo, lavarme, comprobar algo, etc.).",
    "34. Me vienen ideas o imágenes que me dan miedo.",
    "35. Me siento temeroso.",
    "36. Tengo que hacer las cosas muy despacio para estar seguro de que lo hago bien.",
    "37. Me siento solo.",
    "38. Me siento inferior a los demás.",
    "39. Lloro con facilidad.",
    "40. Me siento solo, aunque tenga compañía.",
    "41. Me da por gritar o tirar las cosas.",
    "42. Me siento inútil o poco valioso.",
    "43. Me duelen los músculos.",
    "44. Discuto con frecuencia.",
    "45. Tengo dolores en el corazón o en el pecho.",
    "46. Me dan ahogos o me cuesta respirar.",
    "47. Tengo que evitar ciertas cosas, lugares o actividades porque me dan miedo.",
    "48. Me dan ganas de golpear o hacer daño a alguien.",
    "49. Siento que todo requiere un gran esfuerzo.",
    "50. Tengo presentimientos de que va a pasar algo malo.",
]
OPCIONES_LSB50 = {
    0: "0 - Nada",
    1: "1 - Poco",
    2: "2 - Moderadamente",
    3: "3 - Bastante",
    4: "4 - Mucho",
}

MAPA_TESTS = {
    "LSB-50": {"items": ITEMS_LSB50, "opciones": OPCIONES_LSB50},
}

# -----------------------------------------------------------------------------
# DETECCIÓN DE PARÁMETROS URL
# -----------------------------------------------------------------------------
query_params = st.query_params
token_url = query_params.get("token", None)

if token_url and "token_activo" not in st.session_state:
    token_limpio = token_url.strip().upper()
    datos_actuales = cargar_datos_db()
    if token_limpio in datos_actuales:
        if datos_actuales[token_limpio].get("estado") == "finalizado":
            st.error("Este enlace ya ha sido utilizado y finalizado.")
        else:
            st.session_state["token_activo"] = token_limpio
            st.query_params.clear()

# -----------------------------------------------------------------------------
# 3. BARRA LATERAL RESTRICTORA (ACCESO PERITO)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.title("🔒 Acceso Profesional")

    if not st.session_state["perito_autenticado"]:
        with st.expander("🔑 Iniciar Sesión Perito"):
            pass_input = st.text_input(
                "Contraseña Maestra:",
                type="password",
                key="input_pass_perito",
                autocomplete="off",
            )
            if st.button("Acceder", use_container_width=True):
                if pass_input == CONTRASEÑA_MAESTRA:
                    st.session_state["perito_autenticado"] = True
                    st.rerun()
                else:
                    st.error("Contraseña incorrecta.")
    else:
        st.success("🟢 Sesión Pericial Activa")
        if st.button("🔴 Cerrar Sesión Perito", use_container_width=True):
            st.session_state["perito_autenticado"] = False
            st.rerun()

# -----------------------------------------------------------------------------
# 4. RUTEO DE INTERFAZ (EVALUADO vs PANEL PERICIAL)
# -----------------------------------------------------------------------------
if st.session_state["perito_autenticado"]:
    st.title("🔒 Panel Pericial de Administración")
    st.write("Módulo pericial de gestión de evaluaciones y cadena de custodia.")
    st.divider()

    st.subheader("🔑 Generar Clave y Link de Acceso")
    if st.button("🎲 Generar Nueva Clave y Link", type="primary"):
        nueva_clave = generar_token_unico()
        ip_perito, ua_perito = obtener_metadatos_conexion()
        info_nueva = {
            "estado": "activa",
            "datos_persona": None,
            "evaluaciones": {},
            "ip_acceso": ip_perito,
            "user_agent": ua_perito,
        }
        guardar_token_db(nueva_clave, info_nueva)

        st.success(f"¡Clave generada con éxito!: **`{nueva_clave}`**")
        base_url = "https://psi-forense-hwgpyudkkkwqfwsjx2kkge.streamlit.app"
        link_completo = f"{base_url}/?token={nueva_clave}"
        st.code(link_completo, language="text")

    st.divider()
    st.subheader("📋 Estado de Claves y Evaluaciones")

    claves_globales = cargar_datos_db()

    if claves_globales:
        for clave in list(claves_globales.keys()):
            info = claves_globales[clave]
            persona = info.get("datos_persona")
            evals = info.get("evaluaciones", {})
            estado_token = info.get("estado", "activa")

            col_texto, col_btn_ver, col_actualizar, col_borrar = st.columns([3.5, 1.8, 1.2, 1.0])

            with col_texto:
                if estado_token == "finalizado":
                    nombre_str = persona["nombre"] if persona else "Desconocido"
                    st.markdown(f"🔒 **Clave:** `{clave}` | **Estado:** Finalizado ({nombre_str})")
                elif not evals and not persona:
                    st.markdown(f"🟢 **Clave:** `{clave}` | **Estado:** Disponible")
                elif not evals:
                    info_persona = f" ({persona['nombre']})" if persona else ""
                    st.markdown(f"🟢 **Clave:** `{clave}` | **Estado:** En proceso{info_persona}")
                else:
                    nombre_str = persona["nombre"] if persona else "Desconocido"
                    tests_realizados = ", ".join(list(evals.keys()))
                    st.markdown(f"🔴 **Clave:** `{clave}` | **Eval:** {nombre_str} | **Pruebas:** {tests_realizados}")

            with col_btn_ver:
                if persona:
                    if f"modal_ver_{clave}" not in st.session_state:
                        st.session_state[f"modal_ver_{clave}"] = False

                    btn_label = (
                        "👁️ Ocultar"
                        if st.session_state[f"modal_ver_{clave}"]
                        else "👁️ Ver Protocolo"
                    )

                    if st.button(btn_label, key=f"btn_ver_{clave}", use_container_width=True):
                        st.session_state[f"modal_ver_{clave}"] = not st.session_state[f"modal_ver_{clave}"]
                        st.rerun()
                else:
                    st.write("_Sin datos_")

            with col_actualizar:
                if st.button("🔄 Actualizar", key=f"btn_actualizar_{clave}", use_container_width=True):
                    st.rerun()

            with col_borrar:
                if st.button("🗑️ Borrar", key=f"btn_borrar_{clave}", use_container_width=True):
                    if st.session_state.get("token_activo") == clave:
                        del st.session_state["token_activo"]
                    if f"modal_ver_{clave}" in st.session_state:
                        del st.session_state[f"modal_ver_{clave}"]
                    eliminar_token_db(clave)
                    st.rerun()

            if st.session_state.get(f"modal_ver_{clave}", False):
                with st.container():
                    st.info(f"### 🛡️ Protocolo y Trazabilidad Forense - Token: `{clave}`")
                    if persona:
                        st.write(f"**Nombre y Apellido:** {persona.get('nombre', 'N/A')}")
                        st.write(f"**Número de DNI:** {persona.get('dni', 'N/A')}")
                        st.write(f"**Localidad:** {persona.get('localidad', 'N/A')}")
                        st.write(f"**Nacionalidad:** {persona.get('nacionalidad', 'N/A')}")
                        st.write(f"**Fecha y Hora de Registro:** {persona.get('fecha', 'N/A')} - {persona.get('hora', 'N/A')} hs")
                        
                        # -----------------------------------------------------
                        # CONSTANCIA FORMAL DE CONSENTIMIENTO INFORMADO EN PERITO
                        # -----------------------------------------------------
                        st.markdown("---")
                        st.markdown("#### 📜 Constancia de Consentimiento Informado")
                        
                        if persona.get("consentimiento_aceptado"):
                            st.success(
                                f"✅ **CONSENTIMIENTO INFORMADO ACEPTADO**\n\n"
                                f"• **Fecha y Hora de Firma:** {persona.get('fecha_consentimiento', 'N/A')}\n\n"
                                f"• **Firmante:** {persona.get('nombre')} (DNI: {persona.get('dni')})\n\n"
                                f"• **IP de Origen:** `{info.get('ip_acceso', 'N/A')}`\n\n"
                                f"• **Hash de Trazabilidad:** `{persona.get('hash_identidad', 'N/A')}`\n\n"
                                f"• **Declaración:** *'He leído, comprendo y acepto los términos del Consentimiento Informado para Tele-Evaluación Psicológica Forense.'*"
                            )
                        else:
                            st.warning("⚠️ **CONSENTIMIENTO INFORMADO PENDIENTE DE ACEPTACIÓN**")

                        st.markdown("---")
                        st.write(f"**Hash del Bloque (Inalterabilidad):** `{info.get('hash_bloque', 'N/A')}`")
                        st.write(f"**Dispositivo (User-Agent):** `{info.get('user_agent', 'N/A')}`")

                    else:
                        st.warning("El evaluado aún no ha completado sus datos filiatorios.")

                    if evals:
                        st.write("---")
                        st.write("#### 📊 Respuestas Detalladas de las Pruebas:")
                        for test_nombre, respuestas_dict in evals.items():
                            st.markdown(f"**Instrumento:** `{test_nombre}`")
                            if respuestas_dict:
                                tabla_datos = []
                                key_test = None
                                for k in MAPA_TESTS.keys():
                                    if k in test_nombre:
                                        key_test = k
                                        break

                                for idx, (p_key, resp_val) in enumerate(respuestas_dict.items(), 0):
                                    consigna_texto = f"Ítem {idx + 1}"
                                    if key_test and idx < len(MAPA_TESTS[key_test]["items"]):
                                        consigna_texto = MAPA_TESTS[key_test]["items"][idx]

                                    respuesta_texto = str(resp_val)
                                    if key_test and MAPA_TESTS[key_test]["opciones"]:
                                        map_ops = MAPA_TESTS[key_test]["opciones"]
                                        if resp_val in map_ops:
                                            respuesta_texto = map_ops[resp_val]
                                    tabla_datos.append({
                                        "Consigna / Ítem": consigna_texto,
                                        "Respuesta": respuesta_texto,
                                    })
                                st.dataframe(
                                    tabla_datos,
                                    key=f"df_{clave}_{test_nombre}",
                                    use_container_width=True,
                                    hide_index=True,
                                )
                    else:
                        st.write("_Aún no se han registrado respuestas completadas para esta clave._")
                    st.write("_________________________________________________")

            st.divider()
    else:
        st.write("No hay claves generadas todavía en este ciclo.")

else:
    st.title("⚖️ Evaluaciones Psicológicas Forenses")

    ip_cliente, ua_cliente = obtener_metadatos_conexion()
    claves_globales = cargar_datos_db()

    if "token_activo" in st.session_state:
        if st.session_state["token_activo"] not in claves_globales:
            del st.session_state["token_activo"]

    if "token_activo" not in st.session_state:
        st.subheader("🔑 Acceso a Evaluación")
        st.write("Ingrese el **código de acceso** enviado por el profesional:")

        clave_ingresada = st.text_input(
            "Código asignado:",
            key="input_codigo_evaluado_unico",
            placeholder="Ej: EVAL-SS4BJQ",
            autocomplete="off",
        )

        if st.button("Ingresar", use_container_width=True):
            clave_limpia = clave_ingresada.strip().upper()
            if clave_limpia in claves_globales:
                estado_token = claves_globales[clave_limpia].get("estado", "activa")
                if estado_token == "finalizado":
                    st.error("Este token ya ha sido utilizado y finalizado.")
                else:
                    st.session_state["token_activo"] = clave_limpia
                    st.session_state["test_enviado"] = False
                    st.rerun()
            else:
                st.error("Código inválido o inexistente.")

    else:
        token_actual = st.session_state["token_activo"]
        claves_globales = cargar_datos_db()
        datos_token = claves_globales.get(
            token_actual,
            {"estado": "activa", "datos_persona": None, "evaluaciones": {}},
        )

        if datos_token.get("estado") == "finalizado":
            st.error("Este token ya ha sido finalizado. Su sesión ha caducado.")
            if st.button("Aceptar e ir al inicio", use_container_width=True):
                del st.session_state["token_activo"]
                st.rerun()
        else:
            # PASO 1: DATOS FILIATORIOS
            if datos_token.get("datos_persona") is None:
                st.subheader("📋 Datos del Evaluado y Registro de Identidad")
                st.write("Complete sus datos filiatorios para continuar:")

                with st.form("form_datos_personales"):
                    nombre_comp = st.text_input("Nombre y Apellido completo:", autocomplete="off")
                    dni_val = st.text_input("Número de DNI / Documento:", autocomplete="off")
                    localidad_val = st.text_input("Localidad de residencia:", autocomplete="off")
                    nacionalidad_val = st.text_input("Nacionalidad:", value="Argentina", autocomplete="off")

                    guardar_datos = st.form_submit_button("Continuar al Consentimiento Informado", use_container_width=True)

                    if guardar_datos:
                        if nombre_comp.strip() != "" and dni_val.strip() != "" and localidad_val.strip() != "":
                            try:
                                tz_ba = ZoneInfo("America/Argentina/Buenos_Aires")
                                ahora_ba = datetime.now(tz_ba)
                            except Exception:
                                tz_ba = timezone(timedelta(hours=-3))
                                ahora_ba = datetime.now(tz_ba)

                            fecha_eval = ahora_ba.strftime("%Y-%m-%d")
                            hora_eval = ahora_ba.strftime("%H:%M:%S")

                            str_para_hash = f"{token_actual}-{nombre_comp.strip()}-{dni_val.strip()}-{localidad_val.strip()}-{fecha_eval}-{hora_eval}-{ip_cliente}"
                            hash_generado = hashlib.sha256(str_para_hash.encode("utf-8")).hexdigest()

                            datos_token["datos_persona"] = {
                                "nombre": nombre_comp.strip(),
                                "dni": dni_val.strip(),
                                "localidad": localidad_val.strip(),
                                "nacionalidad": nacionalidad_val.strip(),
                                "fecha": fecha_eval,
                                "hora": hora_eval,
                                "hash_identidad": hash_generado,
                                "consentimiento_aceptado": False,
                                "fecha_consentimiento": None,
                            }
                            datos_token["ip_acceso"] = ip_cliente
                            datos_token["user_agent"] = ua_cliente

                            guardar_token_db(token_actual, datos_token)
                            st.rerun()
                        else:
                            st.warning("Por favor complete todos los campos obligatorios.")

            # PASO 2: CONSENTIMIENTO INFORMADO
            elif not datos_token.get("datos_persona", {}).get("consentimiento_aceptado", False):
                persona = datos_token["datos_persona"]
                localidad_eval = persona.get("localidad", "N/A")

                st.subheader("📜 Consentimiento Informado Tele-Evaluación Psicológica")
                st.info(
                    f"Evaluado/a: **{persona['nombre']}** | DNI: **{persona['dni']}** | Localidad: **{localidad_eval}**"
                )

                st.markdown("""
                **TÉRMINOS Y CONDICIONES DEL PROCESO EVALUATIVO:**
                
                1. **Carácter Pericial:** Acepto participar voluntariamente del proceso de tele-evaluación psicológica forense.
                2. **Protección de Datos y Trazabilidad:** Reconozco que mis respuestas y los metadatos de mi conexión (IP, fecha y hora) serán resguardados con cifrado criptográfico para garantizar la validez forense del protocolo.
                3. **Uso Exclusivo:** La información obtenida será utilizada de manera estricta para la confección del informe pericial correspondiente.
                """)

                acepta_check = st.checkbox("He leído, comprendo y acepto expresamente los términos del Consentimiento Informado.")

                if st.button("✍️ Confirmar y Comenzar Evaluación", type="primary", use_container_width=True):
                    if acepta_check:
                        try:
                            tz_ba = ZoneInfo("America/Argentina/Buenos_Aires")
                            ahora_ba = datetime.now(tz_ba)
                        except Exception:
                            tz_ba = timezone(timedelta(hours=-3))
                            ahora_ba = datetime.now(tz_ba)

                        persona["consentimiento_aceptado"] = True
                        persona["fecha_consentimiento"] = ahora_ba.strftime("%Y-%m-%d %H:%M:%S")
                        datos_token["datos_persona"] = persona

                        guardar_token_db(token_actual, datos_token)
                        st.success("Consentimiento otorgado con éxito.")
                        st.rerun()
                    else:
                        st.error("Debe marcar la casilla de aceptación para continuar.")

            # PASO 3: INSTRUMENTOS DE EVALUACIÓN
            else:
                st.success(f"Bienvenido/a **{datos_token['datos_persona']['nombre']}**. Puede iniciar el completamiento de la prueba.")
                st.info("Complete los reactivos presentados a continuación y presione 'Enviar Evaluación' al finalizar.")
