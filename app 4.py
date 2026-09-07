import streamlit as st
import hashlib
from datetime import datetime
import pytz

# Configuración de la página
st.set_page_config(
    page_title="Evaluaciones Psicológicas Forenses",
    page_icon="⚖️",
    layout="wide"
)

# Definir zona horaria de Buenos Aires
tz_ba = pytz.timezone('America/Argentina/Buenos_Aires')

# Inicializar st.session_state para claves y datos si no existen
if "claves" not in st.session_state:
    st.session_state["claves"] = []

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

# --- MAPA DE TESTS E ÍTEMS (Ejemplo LSB-50 y otros) ---
MAPA_TESTS = {
    "LSB-50": {
        "titulo": "LSB-50 (Listado de Síntomas Breve)",
        "items": [
            "1. Dolor de cabeza",
            "2. Nerviosismo o temblores",
            "3. Desánimo o tristeza",
            "4. Dificultad para concentrarse",
            "5. Sentimiento de que otros te culpan"
        ],
        "opciones": {0: "Nunca", 1: "Poco", 2: "Moderadamente", 3: "Bastante", 4: "Mucho"}
    }
}

# --- CONTROL DE ACCESO PERICIAL (Sidebar) ---
st.sidebar.markdown("## 🔐 Acceso Profesional")
modo_perito = st.sidebar.toggle("Iniciar Sesión Perito", value=st.session_state["logged_in"])

if modo_perito:
    st.session_state["logged_in"] = True
    st.sidebar.success("🟢 Sesión Pericial Activa")
    if st.sidebar.button("Cerrar Sesión Perito"):
        st.session_state["logged_in"] = False
        st.rerun()
else:
    st.session_state["logged_in"] = False

# --- GESTIÓN DE TOKENS (URL Query Parameters) ---
query_params = st.query_params
token_url = query_params.get("token", None)

# --- VISTA PANEL DE ADMINISTRACIÓN / PERITO ---
if st.session_state["logged_in"]:
    st.title("⚖️ Panel Pericial - Gestión de Evaluaciones")
    st.markdown("---")
    
    st.markdown("### 🔑 Generar Nueva Clave / Token de Evaluación")
    col_g1, col_g2 = st.columns([2, 1])
    with col_g1:
        nuevo_id = st.text_input("Identificador del Evaluado (Opcional)", placeholder="Ej: JuanPerez o Caso402")
    with col_g2:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button("Generar Token Único", use_container_width=True):
            hash_token = hashlib.sha256(str(datetime.now(tz_ba)).encode()).hexdigest()[:6].upper()
            token_generado = f"EVAL-{hash_token}"
            if token_generado not in st.session_state["claves"]:
                st.session_state["claves"].append(token_generado)
                st.success(f"Token generado con éxito: `{token_generado}`")
                st.rerun()

    st.markdown("---")
    st.markdown("### 📋 Estado de Claves y Evaluaciones")

    # Control global para expandir o colapsar todos los protocolos
    col_master1, col_master2 = st.columns([2, 4])
    with col_master1:
        ver_todos_global = st.toggle("📂 Expandir todos los protocolos", value=False)

    st.markdown("---")

    # Iterar sobre todas las claves generadas en el sistema
    for clave in st.session_state.get("claves", []):
        persona = st.session_state.get(f"persona_{clave}", {})
        evals = st.session_state.get(f"evaluaciones_{clave}", {})
        
        # Estructura en tres columnas para cada clave
        col_texto, col_btn_ver, col_borrar = st.columns([4, 2, 1])
        
        with col_texto:
            if persona:
                nombres_tests = ", ".join(evals.keys()) if evals else "Datos filiatorios cargados"
                st.markdown(f"🟢 **Clave:** `{clave}` | **Eval:** {persona.get('nombre', 'N/A')} (DNI: {persona.get('dni', 'N/A')}) | **Pruebas:** {nombres_tests}")
            else:
                st.markdown(f"🔴 **Clave:** `{clave}` | *Estado: Disponible (Pendiente)*")
                
        with col_btn_ver:
            if persona or evals:
                btn_label = "👁️ Ver Protocolo" if evals else "👤 Ver Datos"
                
                # Si el interruptor global está activado, forzamos la apertura de este protocolo
                if ver_todos_global:
                    st.session_state[f"modal_ver_{clave}"] = True
                    
                if st.button(btn_label, key=f"ver_det_{clave}", use_container_width=True):
                    st.session_state[f"modal_ver_{clave}"] = not st.session_state.get(f"modal_ver_{clave}", False)
            else:
                st.markdown("<div style='text-align: center; color: gray; padding-top: 8px;'>Sin datos aún</div>", unsafe_allow_html=True)
                
        with col_borrar:
            if st.button("🗑️ Borrar", key=f"borrar_{clave}", use_container_width=True):
                if f"persona_{clave}" in st.session_state: del st.session_state[f"persona_{clave}"]
                if f"evaluaciones_{clave}" in st.session_state: del st.session_state[f"evaluaciones_{clave}"]
                if clave in st.session_state.get("claves", []):
                    st.session_state["claves"].remove(clave)
                st.rerun()

        # Contenedor de visualización detallada por evaluado (se despliega individualmente o con el toggle global)
        if st.session_state.get(f"modal_ver_{clave}", False):
            with st.container():
                st.markdown(f"---")
                st.info(f"🛡️ **Protocolo Forense Consolidado — Token: `{clave}`**")
                
                if persona:
                    col_info1, col_info2 = st.columns(2)
                    with col_info1:
                        st.write(f"**Nombre y Apellido:** {persona.get('nombre', 'N/A')}")
                        st.write(f"**DNI:** {persona.get('dni', 'N/A')}")
                    with col_info2:
                        st.write(f"**Fecha y Hora:** {persona.get('fecha', 'N/A')} - {persona.get('hora', 'N/A')} hs")
                        st.write(f"**Hash SHA-256:** `{persona.get('hash_seguridad', 'N/A')}`")
                else:
                    st.warning("El evaluado aún no completó sus datos filiatorios.")
                    
                if evals:
                    st.markdown("#### 📊 Batería de Pruebas Completadas:")
                    for test_nombre, respuestas_dict in evals.items():
                        st.markdown(f"**Instrumento:** `{test_nombre}`")
                        if respuestas_dict:
                            tabla_datos = [{"Ítem / Consigna": k, "Respuesta": v} for k, v in respuestas_dict.items()]
                            st.dataframe(tabla_datos, use_container_width=True, hide_index=True)
                else:
                    st.write("_No hay tests completados bajo este token todavía._")
                st.markdown(f"---")
                
        st.markdown("---")

    # Reporte global en texto plano para auditoría rápida
    if st.checkbox("🔍 Mostrar Vista Maestra Consolidada (Todas las respuestas del sistema en un solo reporte)"):
        st.markdown("### 📑 Reporte Global de Peritajes")
        total_evaluados_con_datos = 0
        for clave in st.session_state.get("claves", []):
            p = st.session_state.get(f"persona_{clave}", {})
            e = st.session_state.get(f"evaluaciones_{clave}", {})
            if p or e:
                total_evaluados_con_datos += 1
                st.markdown(f"**Sujeto:** {p.get('nombre', 'Anónimo')} | **DNI:** {p.get('dni', 'S/D')} | **Token:** `{clave}`")
                if e:
                    for t_name, t_ans in e.items():
                        st.text(f"  └─ Test: {t_name} ({len(t_ans)} respuestas registradas)")
                else:
                    st.text("  └─ Sin tests finalizados aún.")
        if total_evaluados_con_datos == 0:
            st.info("No hay registros completos en el sistema para consolidar todavía.")

# --- VISTA PLATAFORMA PRINCIPAL DEL EVALUADO ---
else:
    st.title("⚖️ Evaluaciones Psicológicas Forenses")
    
    if not token_url:
        st.warning("⚠️ Acceso restringido. Por favor, ingrese a través del enlace único provisto por el perito.")
    elif token_url not in st.session_state.get("claves", []):
        st.error("❌ El token ingresado no es válido o ya ha sido dado de baja.")
    else:
        # Inicializar estado para esta sesión de evaluado
        if f"etapa_{token_url}" not in st.session_state:
            st.session_state[f"etapa_{token_url}"] = "datos" # Etapas: datos, menu, test, fin

        # Verificar si ya completó datos filiatorios
        persona_data = st.session_state.get(f"persona_{token_url}", None)

        if not persona_data and st.session_state[f"etapa_{token_url}"] == "datos":
            st.subheader("📝 Registro de Datos Filiatorios")
            with st.form(key=f"form_filiatorios_{token_url}"):
                nombre_input = st.text_input("Nombre y Apellido")
                dni_input = st.text_input("Número de DNI")
                submit_datos = st.form_submit_button("Guardar y Continuar")
                
                if submit_datos:
                    if nombre_input and dni_input:
                        now_ba = datetime.now(tz_ba)
                        f_str = now_ba.strftime("%Y-%m-%d")
                        h_str = now_ba.strftime("%H:%M:%S")
                        hash_data = hashlib.sha256(f"{nombre_input}{dni_input}{now_ba}".encode()).hexdigest()
                        
                        st.session_state[f"persona_{token_url}"] = {
                            "nombre": nombre_input,
                            "dni": dni_input,
                            "fecha": f_str,
                            "hora": h_str,
                            "hash_seguridad": hash_data
                        }
                        st.session_state[f"etapa_{token_url}"] = "menu"
                        st.rerun()
                    else:
                        st.error("Por favor, complete todos los campos obligatorios.")
        else:
            # Mostrar barra superior de estado del evaluado
            p_info = st.session_state.get(f"persona_{token_url}", {})
            st.info(f"Evaluado: **{p_info.get('nombre', 'N/A')}** | DNI: **{p_info.get('dni', 'N/A')}** | Hora (BA): **{p_info.get('hora', 'N/A')}** | Hash: `{p_info.get('hash_seguridad', '')[:10]}...`")

            etapa_actual = st.session_state.get(f"etapa_{token_url}", "menu")

            if etapa_actual == "menu":
                st.markdown("### Seleccione la escala o test a completar:")
                if st.button("📋 LSB-50 (Listado de Síntomas Breve)", use_container_width=True):
                    st.session_state[f"etapa_{token_url}"] = "test_LSB-50"
                    st.rerun()

            elif etapa_actual.startswith("test_"):
                test_key = etapa_actual.replace("test_", "")
                info_test = MAPA_TESTS.get(test_key, {})
                
                st.subheader(info_test.get("titulo", test_key))
                
                with st.form(key=f"form_test_{token_url}_{test_key}"):
                    respuestas_temp = {}
                    for idx, item in enumerate(info_test["items"]):
                        respuestas_temp[item] = st.radio(
                            item, 
                            options=list(info_test["opciones"].keys()), 
                            format_func=lambda x: info_test["opciones"][x],
                            key=f"r_{token_url}_{test_key}_{idx}",
                            horizontal=True
                        )
                    
                    submit_test = st.form_submit_button("📤 Enviar Escala")
                    if submit_test:
                        if f"evaluaciones_{token_url}" not in st.session_state:
                            st.session_state[f"evaluaciones_{token_url}"] = {}
                        
                        st.session_state[f"evaluaciones_{token_url}"][test_key] = respuestas_temp
                        st.session_state[f"etapa_{token_url}"] = "fin"
                        st.rerun()

            elif etapa_actual == "fin":
                st.success("¡Escala enviada y registrada con éxito bajo cadena de custodia digital!")
                st.write("Sus respuestas han sido almacenadas de manera segura para el perito.")
                
                if st.button("🏠 Completar otra escala / Volver al menú"):
                    st.session_state[f"etapa_{token_url}"] = "menu"
                    st.rerun()
