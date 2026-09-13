import hashlib
import json
import random
import string
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import streamlit as st
import psycopg2

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN Y CONEXIÓN A POSTGRESQL (SUPABASE)
# -----------------------------------------------------------------------------
CONTRASEÑA_MAESTRA = st.secrets.get("CONTRASEÑA_MAESTRA", "MiClavePericial2026")

def get_db_connection():
    db_config = st.secrets["postgres"]
    conn = psycopg2.connect(
        host=db_config["host"],
        database=db_config["database"],
        user=db_config["user"],
        password=db_config["password"],
        port=db_config["port"]
    )
    return conn

def init_db():
    conn = get_db_connection()
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
    cursor.close()
    conn.close()

# Inicializar la base de datos en la nube al arrancar la app
init_db()

def cargar_datos_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT token, estado, datos_persona, evaluaciones, ip_acceso, user_agent, hash_bloque FROM evaluaciones_periciales"
    )
    rows = cursor.fetchall()
    cursor.close()
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
    conn = get_db_connection()
    cursor = conn.cursor()

    # En PostgreSQL utilizamos ctid o un ORDER BY numérico si existiera para obtener el último hash de la cadena
    cursor.execute("SELECT hash_bloque FROM evaluaciones_periciales ORDER BY ctid DESC LIMIT 1")
    ultimo = cursor.fetchone()
    hash_prev = ultimo[0] if ultimo and ultimo[0] else "GENESIS_BLOCK_FORENSE"

    payload_str = f"{token}-{json.dumps(info_dict.get('evaluaciones'))}-{info_dict.get('ip_acceso', '')}-{hash_prev}"
    hash_actual = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

    # Sustitución de INSERT OR REPLACE de SQLite por UPSERT nativo de PostgreSQL
    cursor.execute("""
        INSERT INTO evaluaciones_periciales 
        (token, estado, datos_persona, evaluaciones, ip_acceso, user_agent, hash_anterior, hash_bloque)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (token) 
        DO UPDATE SET 
            estado = EXCLUDED.estado,
            datos_persona = EXCLUDED.datos_persona,
            evaluaciones = EXCLUDED.evaluaciones,
            ip_acceso = EXCLUDED.ip_acceso,
            user_agent = EXCLUDED.user_agent,
            hash_anterior = EXCLUDED.hash_anterior,
            hash_bloque = EXCLUDED.hash_bloque
    """, (
        token,
        info_dict.get("estado", "activa"),
        json.dumps(info_dict.get("datos_persona")),
        json.dumps(info_dict.get("evaluaciones", {})),
        info_dict.get("ip_acceso", "Desconocida"),
        info_dict.get("user_agent", "Desconocido"),
        hash_prev,
        hash_actual,
    ))
    conn.commit()
    cursor.close()
    conn.close()

def eliminar_token_db(token):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM evaluaciones_periciales WHERE token = %s", (token,))
    conn.commit()
    cursor.close()
    conn.close()
    
