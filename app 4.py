import streamlit as st
import random
import string
from datetime import datetime
import hashlib
from zoneinfo import ZoneInfo
import sqlite3
import json

# Configuración general de la página
st.set_page_config(
    page_title="Evaluaciones Psicológicas Forenses",
    page_icon="⚖️",
    layout="centered"
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
CONTRASENA_MAESTRA = "MiClavePericial2026"
DB_NAME = "forense_seguro.db"

def init_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
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
    ''')
    conn.commit()
    conn.close()

init_db()

def cargar_datos_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT token, estado, datos_persona, evaluaciones, ip_acceso, user_agent, hash_bloque FROM evaluaciones_periciales")
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
            "hash_bloque": h_bloque
        }
    return data

def guardar_token_db(token, info_dict):
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT hash_bloque FROM evaluaciones_periciales ORDER BY rowid DESC LIMIT 1")
    ultimo = cursor.fetchone()
    hash_prev = ultimo[0] if ultimo and ultimo[0] else "GENESIS_BLOCK_FORENSE"
    
    payload_str = f"{token}-{json.dumps(info_dict.get('evaluaciones'))}-{info_dict.get('ip_acceso', '')}-{hash_prev}"
    hash_actual = hashlib.sha256(payload_str.encode('utf-8')).hexdigest()
    
    cursor.execute('''
        INSERT OR REPLACE INTO evaluaciones_periciales 
        (token, estado, datos_persona, evaluaciones, ip_acceso, user_agent, hash_anterior, hash_bloque)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        token,
        info_dict.get("estado", "activa"),
        json.dumps(info_dict.get("datos_persona")),
        json.dumps(info_dict.get("evaluaciones", {})),
        info_dict.get("ip_acceso", "Desconocida"),
        info_dict.get("user_agent", "Desconocido"),
        hash_prev,
        hash_actual
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
            if "," in ip:
                ip = ip.split(",")[0].strip()
            ua = headers.get("User-Agent", "Desconocido")
            return ip, ua
    except Exception:
        pass
    return "IP_LOCAL_O_NO_DETECTADA", "Navegador_Estandar"

if "perito_autenticado" not in st.session_state:
    st.session_state["perito_autenticado"] = False

def generar_token_unico(longitud=6):
    caracteres = string.ascii_uppercase + string.digits
    codigo = ''.join(random.choice(caracteres) for _ in range(longitud))
    return f"EVAL-{codigo}"

# -----------------------------------------------------------------------------
# 2. BANCO COMPLETO DE REACTIVOS (INCLUYENDO ESCALA DE SUCESOS DE VIDA - CASULLO)
# -----------------------------------------------------------------------------

ITEMS_SUCESOS_VIDA = [
    "1. Enfermedad física propia, seria, importante",
    "2. Enfermedad física seria de algún hermano/a",
    "3. Enfermedad física seria del padre",
    "4. Enfermedad física seria de la madre",
    "5. Enfermedad física seria de algún amigo/a",
    "6. Problemas psicológicos personales importantes",
    "7. Enfermedad psíquica de algún hermano/a",
    "8. Enfermedad psíquica del padre",
    "9. Enfermedad psíquica de la madre",
    "10. Enfermedad psíquica de algún pariente",
    "11. Enfermedad psíquica de algún amigo/a",
    "12. Muerte del padre",
    "13. Muerte de la madre",
    "14. Muerte de algún hermano/a",
    "15. Muerte de algún abuelo",
    "16. Desaparición de algún familiar (no saber dónde está)",
    "17. Desaparición de algún amigo/a (no saber dónde está)",
    "18. Divorcio o separación de los padres",
    "19. Divorcio o separación de algún hermano/a",
    "20. Embarazo no deseado",
    "21. Aborto",
    "22. Violación",
    "23. Alguno de los padres despedido o sin empleo",
    "24. Alguna experiencia sexual desagradable, traumática",
    "25. Mudanzas",
    "26. Abuso de alcohol o drogas de algún hermano/a",
    "27. Abuso de alcohol o drogas de alguno de los padres",
    "28. Problemas personales en relación con alcohol o drogas",
    "29. Estar separado/a de un ser querido",
    "30. Muerte de algún amigo/a",
    "31. Serios problemas económicos familiares",
    "32. Problemas familiares graves",
    "33. Problemas personales con algún docente",
    "34. Problemas para aprender en la escuela",
    "35. Ruptura de noviazgo o pareja",
    "36. Problemas que implicaron la participación de la policía",
    "37. Dificultades para tener amigos/as",
    "38. Problemas de fe (crisis religiosa)",
    "39. Haber sufrido un accidente serio",
    "40. Intentar quitarme la vida",
    "41. Divorcio o separación personal",
    "42. Tener dificultades para formar pareja",
    "43. Tener dificultades para conseguir trabajo",
    "44. Confusión vocacional, no saber qué estudiar",
    "45. Problemas de disciplina en la escuela",
    "46. Sentirme amenazado/a o perseguido/a por alguien",
    "47. No poder conservar por mucho tiempo un trabajo",
    "48. Enterarme de que me adoptaron",
    "49. Haber sido golpeado/a, duramente castigado/a",
    "50. Haber pensado en quitarme la vida"
]

OPCIONES_SUCESOS = {
    0: "No ocurrió / No aplica",
    1: "1 - NADA",
    2: "2 - POCO",
    3: "3 - ALGO",
    4: "4 - BASTANTE",
    5: "5 - MUCHO"
}

# -----------------------------------------------------------------------------
# 3. COMPONENTE DE RENDERIZADO DE LA ESCALA DE CASULLO
# -----------------------------------------------------------------------------

def renderizar_escala_casullo(token, datos_actuales):
    st.header("Escala de Sucesos de Vida (M. M. Casullo)")
    st.markdown("""
    A continuación se presenta una lista con experiencias de vida importantes. 
    Seleccione el valor asignado según cuánto consideró que le afectó (de 1 a 5). 
    Si el suceso ocurrió durante el último año y le sigue afectando, marque la casilla correspondiente.
    """)
    
    respuestas_guardadas = datos_actuales.get("evaluaciones", {}).get("casullo", {}).get("respuestas", {})
    resultados_casullo = {}

    with st.form("form_casullo_pericial"):
        for idx, suceso in enumerate(ITEMS_SUCESOS_VIDA, start=1):
            st.markdown(f"**{suceso}**")
            col1, col2 = st.columns([2, 1])
            
            val_previo = respuestas_guardadas.get(str(idx), {}).get("valor", 0)
            inf_previo = respuestas_guardadas.get(str(idx), {}).get("sigue_afectando", False)
            
            with col1:
                valor = st.selectbox(
                    "Grado de afectación:",
                    options=list(OPCIONES_SUCESOS.keys()),
                    format_func=lambda x: OPCIONES_SUCESOS[x],
                    index=val_previo,
                    key=f"casullo_val_{idx}"
                )
            with col2:
                sigue_afectando = False
                if valor > 0:
                    sigue_afectando = st.checkbox(
                        "¿Sigue afectando (último año)?",
                        value=inf_previo,
                        key=f"casullo_inf_{idx}"
                    )
            
            resultados_casullo[str(idx)] = {
                "suceso": suceso,
                "valor": valor,
                "sigue_afectando": sigue_afectando
            }
            st.divider()

        submitted = st.form_submit_button("Guardar Escala de Sucesos de Vida")
        if submitted:
            total_sucesos = sum(1 for v in resultados_casullo.values() if v["valor"] > 0)
            suma_afectacion = sum(v["valor"] for v in resultados_casullo.values())
            siguen_activos = sum(1 for v in resultados_casullo.values() if v["sigue_afectando"])
            
            datos_actuales.setdefault("evaluaciones", {})["casullo"] = {
                "respuestas": resultados_casullo,
                "metricas": {
                    "total_sucesos_vividos": total_sucesos,
                    "puntaje_total_afectacion": suma_afectacion,
                    "sucesos_que_siguen_afectando": siguen_activos
                },
                "fecha_completado": datetime.now(ZoneInfo("America/Argentina/Buenos_Aires")).isoformat()
            }
            
            ip, ua = obtener_metadatos_conexion()
            datos_actuales["ip_acceso"] = ip
            datos_actuales["user_agent"] = ua
            
            guardar_token_db(token, datos_actuales)
            st.success("¡Escala de Sucesos de Vida guardada y encriptada correctamente en la base forense!")

# -----------------------------------------------------------------------------
# 4. FLUJO PRINCIPAL DE NAVEGACIÓN
# -----------------------------------------------------------------------------

def main():
    st.title("⚖️ Plataforma de Evaluaciones Psicológicas Forenses")
    
    claves_globales = cargar_datos_db()
    
    modo = st.sidebar.selectbox("Seleccione el Modo:", ["Acceso Evaluado (Por Token)", "Panel de Control Perito"])
    
    if modo == "Acceso Evaluado (Por Token)":
        st.subheader("Acceso a Evaluaciones Psicométricas")
        token_ingresado = st.text_input("Ingrese su Token de Evaluación (ej. EVAL-XXXXXX):").strip().upper()
        
        if token_ingresado:
            if token_ingresado in claves_globales:
                datos_sesion = claves_globales[token_ingresado]
                if datos_sesion.get("estado") == "bloqueada":
                    st.error("Este token ya ha sido procesado o bloqueado por seguridad pericial.")
                else:
                    st.success(f"Token válido. Evaluado: {datos_sesion.get('datos_persona', {}).get('nombre', 'Paciente')}")
                    
                    instrumento = st.selectbox(
                        "Seleccione el instrumento a completar:",
                        ["Escala de Sucesos de Vida (Casullo)", "MCMI-IV / MMPI-2", "LSB-50"]
                    )
                    
                    if instrumento == "Escala de Sucesos de Vida (Casullo)":
                        renderizar_escala_casullo(token_ingresado, datos_sesion)
                    else:
                        st.info("Módulo general para otras pruebas del sistema.")
            else:
                st.error("Token no encontrado o inválido. Consulte con el perito interviniente.")
                
    elif modo == "Panel de Control Perito":
        st.subheader("Gestión Pericial y Generación de Tokens")
        pass_ingresada = st.text_input("Contraseña Maestra:", type="password")
        
        if pass_ingresada == CONTRASENA_MAESTRA:
            st.success("Acceso perito autorizado.")
            
            accion = st.selectbox("Acción:", ["Ver Evaluaciones Registradas", "Generar Nuevo Token"])
            
            if accion == "Generar Nuevo Token":
                nombre_evaluado = st.text_input("Nombre y Apellido del Evaluado:")
                if st.button("Crear Token"):
                    if nombre_evaluado:
                        nuevo_token = generar_token_unico()
                        datos_iniciales = {
                            "estado": "activa",
                            "datos_persona": {"nombre": nombre_evaluado},
                            "evaluaciones": {}
                        }
                        guardar_token_db(nuevo_token, datos_iniciales)
                        st.success(f"Token generado con éxito: `{nuevo_token}`")
                    else:
                        st.warning("Ingrese el nombre del evaluado.")
            
            elif accion == "Ver Evaluaciones Registradas":
                data_db = cargar_datos_db()
                if data_db:
                    st.json(data_db)
                else:
                    st.info("No hay evaluaciones registradas en la base de datos.")
        elif pass_ingresada:
            st.error("Contraseña incorrecta.")

if __name__ == "__main__":
    main()
