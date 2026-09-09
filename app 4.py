import streamlit as st
import random
import string
from datetime import datetime, timezone, timedelta
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
# OCULTAR MENÚ, FOOTER Y CABECERA DE STREAMLIT (GITHUB / SHARE)
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

claves_globales = cargar_datos_db()

if "perito_autenticado" not in st.session_state:
    st.session_state["perito_autenticado"] = False

def generar_token_unico(longitud=6):
    caracteres = string.ascii_uppercase + string.digits
    codigo = ''.join(random.choice(caracteres) for _ in range(longitud))
    return f"EVAL-{codigo}"

# -----------------------------------------------------------------------------
# 2. BANCO COMPLETO DE REACTIVOS DE LAS PRUEBAS
# -----------------------------------------------------------------------------
ITEMS_LSB50 = [
    "1. Dolores de cabeza", "2. Sensación de mareo o desmayo", "3. Dolores en el pecho o en el corazón",
    "4. Dolores en la parte baja de la espalda", "5. Dolores musculares", "6. Sensación de falta de aire o ahogo",
    "7. Palpitaciones o ritmo cardíaco acelerado", "8. Sensación de debilidad en partes del cuerpo",
    "9. Sensación de pesadez en las piernas", "10. Molestias en el estómago o náuseas",
    "11. Temblores en el cuerpo o en las manos", "12. Sensación de que las cosas no son reales",
    "13. Sensación de estar separado de su propio cuerpo", "14. Pensamientos o ideas fijas que no puede quitarse de la cabeza",
    "15. Necesidad de comprobar las cosas una y otra vez", "16. Dificultad para concentrarse o prestar atención",
    "17. Olvidos o despistes frecuentes", "18. Dificultad para tomar decisiones", "19. Mente en blanco",
    "20. Sensación de que algo malo va a pasar", "21. Miedo repentino o sin razón aparente",
    "22. Sentirse nervioso o interiormente agitado", "23. Sentirse tenso o con sobrecarga emocional",
    "24. Tener miedo en espacios abiertos o en la calle", "25. Miedo a viajar en medios de transporte públicos",
    "26. Miedo a quedarse solo o aislarse", "27. Sentirse triste, decaído o desanimado",
    "28. Pérdida del interés o del placer por las cosas", "29. Sensación de falta de energía o fatiga permanente",
    "30. Sentimientos de culpa o inutilidad", "31. Pensamientos relacionados con la muerte o con hacerse daño",
    "32. Deseo o ideas de acabar con su vida", "33. Sentirse solo incluso estando acompañado",
    "34. Sentir irritabilidad o enfado con facilidad", "35. Accesos o arranques de ira inapropiados",
    "36. Deseos de romper cosas o discutir violentamente", "37. Discusiones frecuentes con los demás",
    "38. Sentirse fácilmente incomodado o molesto", "39. Sentir que las demás personas no le comprenden",
    "40. Sentir que los demás le miran o hablan de usted", "41. Sentir que no se le valora o se le juzga injustamente",
    "42. Sentirse inferior a otras personas", "43. Sensación de timidez o vergüenza ante los demás",
    "44. Problemas o dificultades para conciliar el sueño", "45. Despertarse a mitad de la noche o muy temprano",
    "46. Sueño intranquilo o pesadillas", "47. Pérdida del apetito", "48. Comer en exceso o de forma descontrolada",
    "49. Dificultades o falta de interés en las relaciones sexuales", "50. Sensación de malestar o incomodidad en su cuerpo"
]
OPCIONES_LSB50 = {0: "0 - Nada", 1: "1 - Algo", 2: "2 - Moderadamente", 3: "3 - Bastante", 4: "4 - Mucho"}

ITEMS_MMPI2RF = [
    "1. Me gustan las revistas de mecánica.", "2. Tengo buen apetito.", "3. Me despierto fresco y descansado casi todas las mañanas.",
    "4. Creo que me gustaría el trabajo de bibliotecario.", "5. El ruido me despierta fácilmente.", "6. Mi padre es un buen hombre, o lo fue.",
    "7. Me gusta leer artículos sobre el crimen en los periódicos.", "8. Mis manos y pies suelen estar lo suficientemente calientes.",
    "9. Mi vida diaria está llena de cosas que mantienen mi interés.", "10. Actualmente soy tan capaz para trabajar como lo he sido siempre.",
    "11. Siento un nudo en la garganta la mayor parte del tiempo.", "12. Mi vida sexual es satisfactoria.", "13. La gente debería intentar comprender sus sueños.",
    "14. Me molestan las náuseas y los vómitos.", "15. A veces me dan ganas de maldecir.", "16. Encuentro difícil concentrarme en una tarea.",
    "17. He tenido experiencias muy raras y extrañas.", "18. Rara vez me preocupo por mi salud.", "19. Nunca me he metido en problemas por mi comportamiento sexual.",
    "20. A veces tengo ganas de romper cosas.", "21. Tengo periodos de días, semanas o meses en que no puedo hacer nada.", "22. Mi sueño es variable e inquieto.",
    "23. Gran parte del tiempo me parece que me duele la cabeza por todas partes.", "24. A veces digo mentiras.", "25. Soy más sensitive que la mayoría de la gente.",
    "26. A veces siento que debería hacer algo para dañarme a mí mismo.", "27. Mi salud física es tan buena como la de la mayoría de mis amigos.",
    "28. Nunca he tenido parálisis o debilidad muscular insólita.", "29. A veces me parece que mi mente funciona más despacio de lo habitual.",
    "30. La mayor parte del tiempo me siento feliz.", "31. Siento que la gente lee mis pensamientos.", "32. Me gustaría ser cantante.",
    "33. Creo que la mayoría de la gente mentiría para salir de un problema.", "34. Tengo pocos dolores de cabeza.", "35. A veces pierdo el control de mis actos.",
    "36. Mi conducta está guiada principalmente por las costumbres de quienes me rodean.", "37. Me enfado a veces.", "38. Casi todo me da asco.",
    "39. Soy una persona muy ansiosa.", "40. Creo que me están siguiendo.", "41. La gente me decepciona a menudo.",
    "42. Disfruto de las reuniones sociales.", "43. Siento molestias en la parte superior del abdomen.", "44. Tengo periodos en los que me siento inusualmente alegre sin motivo.",
    "45. Mi memoria parece estar bien.", "46. Me preocupa bastante el dinero.", "47. Me molesta que la gente me pida consejo.",
    "48. Veo cosas, animales o personas que otros no ven.", "49. Tengo dificultades para mantener el equilibrio al caminar.", "50. Me irrita fácilmente la gente.",
    "51. Quisiera no ser tan tímido.", "52. Disfruto de la compañía de los demás.", "53. Tengo ganas de rendirme fácilmente.",
    "54. A veces escucho voces y no sé de dónde vienen.", "55. Me cuesta concentrarme.", "56. Me siento acorralado por las circunstancias.",
    "57. Me gusta la emoción y la aventura.", "58. Tengo problemas de digestión.", "59. Siento que la familia no me apoya.",
    "60. A veces pierdo el sentido del tiempo.", "61. Me cuesta hacer amigos.", "62. Siento que no valgo para nada.",
    "63. Sufro de ataques de pánico repentinos.", "64. Me gusta cocinar.", "65. Siento que la gente habla a mis espaldas.",
    "66. Duermo profundamente toda la noche.", "67. A veces me siento lleno de energía.", "68. Me molesta estar en lugares cerrados.",
    "69. A menudo actúo sin pensar.", "70. Pienso que la vida no vale la pena.", "71. Me agradan los niños.",
    "72. Tengo sensaciones extrañas en la piel.", "73. Me siento seguro al tomar decisiones.", "74. Me cuesta expresar mis sentimientos.",
    "75. Me molesta que cuestionen mis intenciones.", "76. Sufro de temblores en las manos.", "77. Disfruto de la lectura.",
    "78. Me siento distante de los demás.", "79. Me preocupo constantemente por el futuro.", "80. Siento que el mundo está en mi contra.",
    "81. Me molesta el desorden.", "82. Tengo una vida social muy activa.", "83. Me cuesta conciliar el sueño.",
    "84. A veces me siento impulsado a hacer cosas peligrosas.", "85. Confío plenamente en la gente.", "86. Me canso con facilidad.",
    "87. Me gusta planificar mis tareas con anticipación.", "88. Siento opresión en el pecho.", "89. Pienso que las personas son egoístas por naturaleza.",
    "90. Me resulta fácil adaptarme a situaciones nuevas.", "91. Tengo visiones borrosas con frecuencia.", "92. Siento arrepentimiento constante.",
    "93. Me molesta la crítica constructiva.", "94. Me siento lleno de vida y entusiasmo.", "95. Siento que alguien intenta controlar mi mente.",
    "96. Me cuesta pedir ayuda a los demás.", "97. Sufro de mareos repentinos.", "98. Me siento en paz conmigo mismo.",
    "99. A veces siento mucha rabia contenida.", "100. Disfruto de actividades al aire libre.", "101. Siento que nada me satisface.",
    "102. Me preocupa cometer errores en público.", "103. Siento dolor en las articulaciones.", "104. Me resulta sencillo iniciar conversaciones.",
    "105. Me cuesta trabajo mantener el interés en un proyecto.", "106. Creo que la gente abusa de mi confianza.", "107. Me siento triste la mayor parte del tiempo.",
    "108. Me agrada el trabajo en equipo.", "109. Sufro de sudoración excessive.", "110. Me cuesta olvidar ofensas pasadas.",
    "111. Siento que todo me sale mal.", "112. Tengo facilidad para el arte.", "113. A veces oigo zumbidos en los oídos.",
    "114. Siento mucha presión en mi entorno laboral o personal.", "115. Me agrada la rutina diaria.", "116. Pienso que las normas deben seguirse strictly.",
    "117. Me cuesta estar tranquilo en un solo lugar.", "118. Siento que la gente me juzga negativamente.", "119. Me despierto antes de tiempo y no puedo volver a dormir.",
    "120. Me gusta hacer deportes.", "121. Me distraigo con suma facilidad.", "122. Me resulta difícil tomar la iniciativa.",
    "123. Siento hormigueo en mis extremidades.", "124. Disfruto ayudando a personas necesitadas.", "125. Pienso que no hay esperanzas de mejorar.",
    "126. A veces me siento demasiado impulsivo.", "127. Me molesta la impuntualidad.", "128. Me siento querido por mi familia.",
    "129. Siento punzadas de dolor sin causa física.", "130. Me cuesta aceptar las derrotas.", "131. Pienso con claridad la mayor parte del tiempo.",
    "132. Me agrada asistir a teatro o conciertos.", "133. Siento que los demás reciben más de lo que merecen.", "134. Tengo dificultades para respirar con normalidad.",
    "135. Me siento incapaz de resolver mis dilemas.", "136. A veces lloro sin motivo aparente.", "137. Me agrada la investigación científica.",
    "138. Siento que mi mente está llena de pensamientos confusos.", "139. Me molesta que me interrumpan.", "140. Me siento orgulloso de mis logros.",
    "141. Sufro de accesos de tos raras.", "142. Me resulta fácil confiar en mis capacidades.", "143. Me cuesta mostrar afecto hacia los demás.",
    "144. Siento que la suerte jamás me acompaña.", "145. Me atraen las actividades de riesgo.", "146. Tengo estreñimiento o malestar intestinal.",
    "147. Me alegra el éxito de mis amigos.", "148. Me cuesta aceptar cuando cometo un fallo.", "149. Siento miedo en lugares concurridos.",
    "150. Disfruto resolviendo acertijos.", "151. Siento una tensión constante en el cuello.", "152. Me cuesta ponerme en el lugar de otros.",
    "153. A veces me imagino escenarios catastróficos.", "154. Me siento pleno con my trabajo o estudio.", "155. Siento que la gente me evita.",
    "156. Tengo sequedad frecuente en la boca.", "157. Me agrada conocer costumbres distintas.", "158. Me cuesta mantener una disciplina constante.",
    "159. Siento frustración muy rápidamente.", "160. Me despierto con sensación de ahogo.", "161. Me siento optimista frente al futuro.",
    "162. A veces pierdo el apetito por completo.", "163. Me molesta el ruido fuerte.", "164. Siento que nadie me comprende del todo.",
    "165. Me resulta fácil aprender cosas nuevas.", "166. Tengo calambres musculares con frecuencia.", "167. Me cuesta delegar responsabilidades.",
    "168. Siento que pierdo el tiempo a menudo.", "169. Me agradan las labores mecánicas.", "170. Siento latidos acelerados del corazón en reposo.",
    "171. Me cuesta perdonar mis propios errores.", "172. A veces me asalta una profunda tristeza.", "173. Me siento cómodo ante figuras de autoridad.",
    "174. Siento picazón molesta en la piel.", "175. Disfruto de conversaciones profundas.", "176. Me cuesta adaptarme a imprevistos.",
    "177. Siento que me exigen demasiado.", "178. Me desagrada hablar ante un público numeroso.", "179. Tengo episodios de debilidad repentina.",
    "180. Me considero una persona calmada.", "181. Siento que la felicidad es inalcanzable para mí.", "182. Me molesta que impongan reglas arbitrarias.",
    "183. Disfruto coleccionar objetos.", "184. Siento opresión en la cabeza.", "185. Me cuesta expresar desacuerdo con los demás.",
    "186. A veces me cuesta reconocer a personas conocidas.", "187. Me siento satisfecho con mi apariencia.", "188. Siento que los demás son más astutos que yo.",
    "189. Tengo problemas al tragar alimentos.", "190. Me apasiona aprender idiomas.", "191. Me cuesta concentrarse cuando hay distracciones.",
    "192. Siento que la culpa no me deja en paz.", "193. Me agrada hacer plans a largo plazo.", "194. Sufro de dolores de espalda punzantes.",
    "195. Me cuesta trabajo decir que no.", "196. A veces imagino cosas que no son reales.", "197. Me siento motivado día a día.",
    "198. Siento que la competencia me abruma.", "199. Tengo acidez estomacal constante.", "200. Me gusta la jardinería.",
    "201. Me cuesta controlar mis pensamientos negativos.", "202. Siento que los demás se aprovechan de mí.", "203. Me agrada la soledad en su justa medida.",
    "204. Siento pesadez en las extremidades.", "205. Me resulta difícil admitir mis flaquezas.", "206. A veces pierdo la noción de dónde estoy.",
    "207. Me siento respaldado por mi círculo cercano.", "208. Siento envidia del éxito ajeno.", "209. Tengo espasmos oculares molestos.",
    "210. Me atrae la historia antigua.", "211. Me cuesta trabajo establecer prioridades.", "212. Siento que la desesperanza me domina.",
    "213. Me siento capaz de liderar grupos.", "214. Sufro de escalofríos repentinos.", "215. Me cuesta confiar en mis propias decisiones.",
    "216. A veces siento sospechas infundadas.", "217. Me gratifica realizar trabajo comunitario.", "218. Siento ardor en los ojos frecuentemente.",
    "219. Me cuesta mantener un horario regular.", "220. Siento que la suerte nunca está de mi lado.", "221. Disfruto de la música clásica.",
    "222. Siento rigidez muscular en los hombros.", "223. Me cuesta expresar gratitud.", "224. A veces me sobrecoge la soledad.",
    "225. Me siento valorado por mi entorno.", "226. Siento punzadas de malestar general.", "227. Me resulta difícil perdonar la deslealtad.",
    "228. A veces actuaría impulsivamente si no me contuviera.", "229. Me agrada ver documentales educacionales.", "230. Siento latidos irregulares en el pecho.",
    "231. Me cuesta encontrar sentido a la rutina.", "232. Siento que mis metas son alcanzables.", "233. Tengo molestias frecuentes en la garganta.",
    "234. Me cuesta reaccionar con rapidez ante emergencias.", "235. A veces siento una desconexión con la realidad.", "236. Me satisface ayudar a la familia.",
    "237. Siento insensibilidad en partes de mi piel.", "238. Me resulta molesto recibir órdenes.", "239. Me abruma el ritmo acelerado de la sociedad.",
    "240. Disfruto de pasear por la naturaleza.", "241. Siento punzadas en el costado.", "242. Me cuesta reponerme tras una pérdida.",
    "243. Siento que los demás tienen malas intenciones.", "244. Me resulta fácil conservar la compostura.", "245. Tengo pérdida momentánea de audición.",
    "246. Me motiva superar desafíos complejos.", "247. Me cuesta conectar con personas desconocidas.", "248. Siento frustración por no alcanzar la perfección.",
    "249. Me gusta ver eventos deportivos.", "250. Siento ardor de estómago por la noche.", "251. Me resulta complicado tomar iniciativa en grupo.",
    "252. Siento que el pesimismo me abruma.", "253. Me siento agradecido por las oportunidades.", "254. Sufro de cosquilleo continuo en los dedos.",
    "255. Me cuesta trabajo perdonar faltas menores.", "256. A veces pierdo el control emocional brevemente.", "257. Me complace mantener un hogar ordenado.",
    "258. Siento fatiga sin haber hecho esfuerzo.", "259. Me cuesta adaptarme a directrices estrictas.", "260. Siento que my opiniones no cuentan.",
    "261. Disfruto del trabajo artesanal.", "262. Siento palpitaciones al enfrentar problemas.", "263. Me resulta complejo expresar afecto físico.",
    "264. Siento insatisfacción constante.", "265. Me agrada participar en proyectos cívicos.", "266. Tengo pesadez de párpados continua.",
    "267. Me cuesta trabajo seguir instrucciones paso a paso.", "268. A veces dudo de mi propia identidad.", "269. Me siento seguro frente a nuevos proyectos.",
    "270. Siento envidia incontenible por los logros ajenos.", "271. Sufro de rigidez en la mandíbula.", "272. Me apasiona la lectura de biografías.",
    "273. Me resulta complejo manejar la crítica.", "274. Siento que la angustia me paraliza.", "275. Me considero una persona empática.",
    "276. Siento molestias en las articulaciones al despertar.", "277. Me cuesta integrarme a grupos consolidados.", "278. A veces reacciono de forma desmedida.",
    "279. Me gratifica aprender nuevas tecnologías.", "280. Siento vértigo al mirar desde las alturas.", "281. Me resulta difícil superar ofensas pasadas.",
    "282. Siento un vacío profundo a menudo.", "283. Me alegra poder orientar a otros.", "284. Tengo episodios de visión doble.",
    "285. Me cuesta trabajo establecer límites.", "286. A veces me asalta una euforia desmedida.", "287. Me siento cómodo en ambientes estructurados.",
    "288. Siento constante inquietud en las piernas.", "289. Me resulta duro admitir mis errores.", "290. Siento que la suerte nunca está de mi lado.",
    "291. Disfruto del cine dramático.", "292. Siento presión constante en la frente.", "293. Me cuesta empatizar con quienes sufren.",
    "294. Siento que no tengo el control de mi destino.", "295. Me siento capaz de resolver crisis cotidianas.", "296. Sufro de sequedad de piel insoportable.",
    "297. Me cuesta trabajo pedir perdón.", "298. A veces experimento cambios bruscos de humor.", "299. Me resulta gratificante la tranquilidad del hogar.",
    "300. Siento ahogo en espacios reducidos.", "301. Me cuesta confiar en desconocidos.", "302. Siento que mi aporte no tiene valor.",
    "303. Disfruto descubriendo nuevos lugares.", "304. Siento punzadas de molestia en los oídos.", "305. Me cuesta trabajo delegar tareas importantes.",
    "306. A veces me invaden recuerdos del pasado sin querer.", "307. Me siento tranquilo ante los cambios.", "308. Siento irritación por pequeñas faltas ajenas.",
    "309. Sufro de malestar estomacal ante los nervios.", "310. Me interesa la política internacional.", "311. Me resulta complejo expresar gratitud de corazón.",
    "312. Siento que nada tiene sentido en mi entorno.", "313. Me siento satisfecho con mi desempeño general.", "314. Tengo pérdida de sensibilidad táctil temporal.",
    "315. Me cuesta trabajo cumplir horarios estrictos.", "316. A veces prefiero aislarme por completo.", "317. Me agrada mantener limpia mi zona de trabajo.",
    "318. Siento tensión muscular en la espalda baja.", "319. Me resulta difícil aceptar consejos no solicitados.", "320. Siento que el pesimismo me bloquea.",
    "321. Disfruto participando en actividades grupales.", "322. Siento punzadas de dolor en la sien.", "323. Me cuesta trabajo superar fracasos pasados.",
    "324. A veces imagino situaciones inexistentes.", "325. Me siento seguro al asumir riesgos calculados.", "326. Sufro de zumbidos repentinos en los oídos.",
    "327. Me resulta complejo perdonar agravios.", "328. Siento un agotamiento permanente.", "329. Me agrada cuidar el entorno natural.",
    "330. Siento ardor persistente en la piel.", "331. Me cuesta trabajo establecer prioridades claras.", "332. A veces dudo de mis convicciones más profundas.",
    "333. Me siento respetado por mis semejantes.", "334. Siento envidia irracional.", "335. Sufro de malestar articular intermitente.",
    "336. Me atrae la literatura filosófica.", "337. Me resulta difícil admitir derrotas.", "338. Siento que my vida tiene un propósito claro."
]
OPCIONES_MMPI = ["Verdadero", "Falso"]

ITEMS_CUIDA = [
    "1. Tengo problemas para dormir.", "2. Estoy satisfecho de cómo soy.", "3. Si alguien me insulta intento averiguar por qué lo hace.",
    "4. A veces juzgo a los demás sin conocerles.", "5. Me disgusta mi aspecto físico.", "6. Tengo cambios de humor con bastante facilidad.",
    "7. Me gusta reunirme con mis amigos y conversar.", "8. Siempre hago lo que digo.", "9. Hago todo lo posible por salirme con la mía.",
    "10. Me cuesta mucho participar en reuniones de grupo.", "11. Ya no me resulta doloroso pensar en las cosas a las que he tenido que renunciar con los años.",
    "12. Cuando voy de viaje evito relacionarme con otros viajeros.", "13. Me cuesta aceptar que mi relación de pareja no sea como al principio.",
    "14. Me altero fácilmente cuando algo inesperado perturba mi vida cotidiana.", "15. Los sentimientos de los demás no me preocupan.",
    "16. Abandono fácilmente las tareas cuando me encuentro con ciertas dificultades.", "17. Me pongo nervioso cuando alguien me halaga.",
    "18. Habitualmente compro cosas que no necesito sólo porque me apetece.", "19. Me siento angustiado cuando en mi vida ocurre algo que no tengo previsto.",
    "20. Si presto algo y me lo devuelven estropeado, soy incapaz de decir nada.", "21. Tan pronto me siento lleno de vitalidad como profundamente cansado.",
    "22. Cuando alguien me critica injustamente me defiendo dialogando.", "23. Creo que las despedidas me resultan más difíciles que al resto de las personas.",
    "24. A veces me entusiasmo tanto con alguna idea nueva que no pienso en los inconvenientes que pueda tener.", "25. Me siento incómodo cuando alguien se acerca demasiado.",
    "26. Tengo tendencia a enojarme cuando las cosas no me salen bien.", "27. Las dificultades de otros países no nos incumben, es algo que deben solucionárselo ellos.",
    "28. Soy una persona a la que los demás utilizan.", "29. Me es fácil conectar con la gente.", "30. No me preocupa ser rechazado por los demás.",
    "31. Me preocupa que los demás no me quieran.", "32. Cuando surge un problema prefiero que lo resuelva otro.", "33. Me cuesta mucho pedir favores.",
    "34. Cuando estoy ocupado en algo acepto con tranquilidad cualquier interrupción.", "35. A veces pienso que no valgo para nada.", "36. En general, me gusta la gente.",
    "37. Nunca bebo líquidos.", "38. Me encanta organizar fiestas con mis amigos.", "39. En alguna ocasión me he quedado con algo que no era de mi propiedad.",
    "40. No me cuesta trabajo asumir los cambios de mi cuerpo.", "41. Cuando estoy solo me siento triste.", "42. Antes de tomar una decisión suelo tener en cuenta todas las posibilidades.",
    "43. Si mi hijo adolescente me propusiera algo excepcional, en principio estaría dispuesto a escucharle.", "44. Considero que tengo menos cualidades que el resto de las personas.",
    "45. Necesito sentirme arropado por alguien.", "46. Es muy raro que algo o alguien me haga perder los estribos.", "47. Conecto fácilmente con los sentimientos de las personas.",
    "48. Me cuesta mucho desprenderme de los objetos de mi infancia.", "49. No me importa lo que piensen los demás sobre mis opiniones.",
    "50. El que haya organizaciones que presten ayuda a otros países me parece un gasto innecesario.", "51. Suelo reaccionar sin pensar mucho en lo que hago.",
    "52. Ante situaciones conceptuales o peligrosas me altero menos que los demás.", "53. No me suelo alterar por pequeñeces.", "54. Sufro cuando deseo tener o comprar algo que no puedo.",
    "55. Solo me interesan aquellas cosas que están relacionadas con mi campo de interés.", "56. Si en un restaurante recibo un mal servicio hago la reclamación oportuna.",
    "57. Suelo reconocer las cualidades positivas que tengo.", "58. No me cuesta comprometerme emocionalmente con otras personas.", "59. Acepto con naturalidad que alguien diga cosas positivas de mí.",
    "60. Me cuesta comprender otras religiones.", "61. Si alguien me atrae encuentro la forma de establecer comunicación con él.", "62. Hago las cosas sin pararme a pensar.",
    "63. Me cuesta mucho percibir las cualidades positivas que tengo.", "64. Suelo hablar sin pensar demasiado lo que digo.", "65. Me siento mal cuando no tengo relaciones afectivas duraderas con otras personas.",
    "66. Sé controlar mis sentimientos y no dejo que estos me desborden.", "67. No me importa lo que los demás piensen de mí.", "68. Me considero capaz de hacer las cosas tan bien como los demás.",
    "69. Ni en situaciones muy tensas me irrito.", "70. Me da igual que se mueran plantas o animales si yo no los he cuidado.", "71. Me incomoda ver llorar a una persona.",
    "72. Pienso detenidamente las cosas antes de hacerlas.", "73. Me enfado conmigo mismo cuando fallo en algo.", "74. Me asustan los cambios de la vida cotidiana.",
    "75. No me resulta fácil entablar conversación con desconocidos.", "76. Es imposible que me enfade con nadie.", "77. Me angustia que una relación afectiva importante se pueda romper.",
    "78. Me desanimo fácilmente ante los imprevistos.", "79. Comprendo fácilmente el punto de vista de los demás.", "80. Suelo decir siempre la verdad.",
    "81. Ante situaciones difíciles me mantengo sereno.", "82. Si un amigo/a me pide ayuda dejo lo que estoy haciendo y acudo.", "83. Me adapto con facilidad a los cambios de planes.",
    "84. Intento ponerme en el lugar de las personas que sufren.", "85. Si cometo un error prefiero admitirlo que buscar excusas.", "86. Siento que los demás valoran mi trabajo y mi esfuerzo.",
    "87. Me cuesta superar la pérdida de seres queridos.", "88. No me molesta que me lleven la contraria.", "89. Pienso bien las consecuencias antes de actuar.",
    "90. Me resulta fácil expresar mis sentimientos a las personas que quiero.", "91. Acepto las normas aunque a veces no esté de acuerdo.", "92. Tengo confianza en mis capacidades para solucionar problemas.",
    "93. Evito las discusiones innecesarias.", "94. Me resulta difícil pedir perdón cuando me equivoco.", "95. Muestro paciencia ante las dificultades de los demás.",
    "96. Me esfuerzo por entender las opiniones distintas a la mía.", "97. Respeto las decisiones de los demás aunque no las comparta.", "98. Me siento seguro al tomar decisiones importantes.",
    "99. Mantengo la calma aunque las cosas salgan mal.", "100. Sé escuchar atentamente cuando alguien me habla.", "101. Me cuesta controlar el malestar cuando me contradicen.",
    "102. Intento resolver los conflictos buscando el beneficio de todos.", "103. Siento satisfacción cuando ayudo a los demás.", "104. Acepto mis limitaciones personales sin frustrarme.",
    "105. Me cuesta adaptarme a nuevas situaciones laborales o personales.", "106. Trato con respeto a todas las personas independientemente de su condición.", "107. Controlo mis impulsos cuando me siento molesto.",
    "108. Sé decir que no sin sentir culpa.", "109. Me preocupa el bienestar de los niños y personas vulnerables.", "110. Acepto las críticas si son constructivas.",
    "111. Me resulta fácil ponerme en el lugar de los niños.", "112. Sé mantener los límites con firmeza y afecto.", "113. No me dejo llevar por la ira ante las provocaciones.",
    "114. Me considero una persona tolerante.", "115. Sé manejar el estrés en momentos de crisis.", "116. Acepto a las personas tal como son.",
    "117. Me cuesta pedir ayuda cuando me siento desbordado.", "118. Expreso lo que pienso con claridad y respeto.", "119. Me preocupa la injusticia social.",
    "120. Mantengo el compromiso asumido a pesar de las dificultades.", "121. Me resulta fácil establecer un vínculo de confianza.", "122. Admito mis equivocaciones frente a los niños o subordinados.",
    "123. Mantengo una actitud positiva ante la vida.", "124. Sé reaccionar con flexibilidad ante imprevistos graves.", "125. Entiendo la importancia del afecto en la educación.",
    "126. Evito el uso de la violencia verbal o física en cualquier circunstancia.", "127. Me siento capaz de cuidar y proteger a otros.", "128. Sé perdonar las faltas de los demás.",
    "129. Me comunico con claridad y paciencia.", "130. Acepto que los demás tengan prioridades distintas a las mías.", "131. Mantengo el autocontrol cuando me siento presionado.",
    "132. Me involucro de forma activa en la resolución de problemas comunitarios.", "133. Reconozco el esfuerzo de los demás y los felicito.", "134. Sé gestionar mis frustraciones sin desquitarme con otros.",
    "135. Muestro empatía hacia las personas que están pasando por momentos tristes.", "136. Acepto los cambios en las rutinas con naturalidad.", "137. Sé poner los intereses del grupo o familia por encima de los míos cuando es necesario.",
    "138. Mantengo la serenidad durante discusiones acaloradas.", "139. Me resulta fácil expresar ternura.", "140. No me guardo rencor por ofensas pasadas.",
    "141. Busco el diálogo antes de tomar medidas drásticas.", "142. Muestro flexibilidad mental ante posturas opuestas.", "143. Me siento preparado para asumir responsabilidades de cuidado.",
    "144. Respeto el ritmo de aprendizaje o desarrollo de cada persona.", "145. Sé transmitir seguridad y tranquilidad a quienes me rodean.", "146. Acepto con calma las equivocaciones ajenas.",
    "147. Mantengo el entusiasmo a pesar de los obstáculos.", "148. Me adapto sin dificultad a entornos nuevos.", "149. Valoro la honestidad por encima de todo.",
    "150. Sé pedir disculpas si he respondido de forma inadecuada.", "151. Comprendo el impacto de mis acciones en los demás.", "152. Muestro disponibilidad para escuchar las necesidades ajenas.",
    "153. No me desespero cuando las respuestas no son inmediatas.", "154. Acepto la diversidad de pensamiento en mi entorno.", "155. Controlo mis temores ante situaciones desconocidas.",
    "156. Muestro afecto sincero hacia los niños.", "157. Sé poner límites claros sin perder la calma.", "158. Respeto el tiempo de los demás.",
    "159. Acepto con madurez las pérdidas o fracasos.", "160. Busco soluciones constructivas ante los dilemas cotidianos.", "161. Me resulta sencillo ponerme en el lugar de alguien que sufre.",
    "162. Mantengo la coherencia entre lo que digo y hago.", "163. Sé mantener la distancia adecuada sin ser distante ni invasivo.", "164. Me muestro accesible ante las demandas de ayuda.",
    "165. Sé mantener la paz interior en momentos de tensión.", "166. Acepto las reglas de convivencia con agrado.", "167. Me siento capaz de sostener emocionalmente a otro.",
    "168. Muestro paciencia ante las rabieta o berrinches infantiles.", "169. Respeto la intimidad y el espacio ajeno.", "170. Mantengo una actitud de colaboración constante.",
    "171. Sé adaptarme a las exigencias del entorno sin perder mi identidad.", "172. Acepto que las cosas no siempre salgan según lo previsto.", "173. Muestro un interés sincero por las emociones de las personas.",
    "174. Sé manejar la presión de tiempo sin perder los nervios.", "175. Me comunico de manera asertiva y pausada.", "176. Acepto las diferencias individuales con agrado.",
    "177. Mantengo el equilibrio emocional frente al conflicto.", "178. Muestro responsabilidad en el cuidado de terceros.", "179. Sé motivar a los demás en momentos difíciles.",
    "180. Respeto la autoridad legítima.", "181. Acepto mis propios errores sin buscar culpables.", "182. Sé escuchar sin interrumpir.",
    "183. Muestro disposición para el trabajo cooperativo.", "184. Mantengo la objetividad en las evaluaciones personales.", "185. Acepto con gratitud la ayuda que me brindan.",
    "186. Sé brindar protección afectiva y física.", "187. Muestro comprensión ante las debilidades ajenas.", "188. Mantengo la firmeza en mis valores fundamentales.",
    "189. Sé dar respuestas serenas en situaciones críticas."
]
OPCIONES_CUIDA = {
    1: "1 - Completamente en desacuerdo", 
    2: "2 - En desacuerdo", 
    3: "3 - De acuerdo", 
    4: "4 - Completamente de acuerdo"
}

ITEMS_STAI = [
    "1. Me siento calmado/a (Ansiedad Estado)", "2. Me siento seguro/a (Ansiedad Estado)",
    "3. Estoy tenso/a (Ansiedad Estado)", "4. Me siento contrariado/a (Ansiedad Estado)",
    "5. Me siento cómodo/a (Ansiedad Estado)", "6. Me siento alterado/a (Ansiedad Estado)",
    "7. Estoy preocupado/a por posibles desgracias (Ansiedad Estado)", "8. Me siento descansado/a (Ansiedad Estado)",
    "9. Me siento angustiado/a (Ansiedad Estado)", "10. Me siento confortable (Ansiedad Estado)",
    "11. Tengo confianza en mí mismo/a (Ansiedad Estado)", "12. Me siento nervioso/a (Ansiedad Estado)",
    "13. Estoy desasosegado/a (Ansiedad Estado)", "14. Me siento muy atado/a (Ansiedad Estado)",
    "15. Me siento relajado/a (Ansiedad Estado)", "16. Me siento satisfecho/a (Ansiedad Estado)",
    "17. Estoy preocupado/a (Ansiedad Estado)", "18. Me siento aturdido/a o sobreexcitado/a (Ansiedad Estado)",
    "19. Me siento alegre (Ansiedad Estado)", "20. Me siento de buen humor (Ansiedad Estado)",
    "21. Me siento bien (Ansiedad Rasgo)", "22. Me canso rápidamente (Ansiedad Rasgo)",
    "23. Siento ganas de llorar (Ansiedad Rasgo)", "24. Desearía ser tan feliz como otros parecen serlo (Ansiedad Rasgo)",
    "25. Pierdo oportunidades por no decidirme pronto (Ansiedad Rasgo)", "26. Me siento descansado/a (Ansiedad Rasgo)",
    "27. Soy una persona tranquila, serena y sosegada (Ansiedad Rasgo)", "28. Siento que las dificultades se me acumulan al punto de no poder superarlas (Ansiedad Rasgo)",
    "29. Me preocupo demasiado por cosas que no tienen importancia (Ansiedad Rasgo)", "30. Soy feliz (Ansiedad Rasgo)",
    "31. Siento tendencia a tomar las cosas muy a pecho (Ansiedad Rasgo)", "32. Me falta confianza en mí mismo/a (Ansiedad Rasgo)",
    "33. Me siento seguro/a (Ansiedad Rasgo)", "34. Evito enfrentarme a las crisis o dificultades (Ansiedad Rasgo)",
    "35. Me siento melancólico/a (Ansiedad Rasgo)", "36. Me siento satisfecho/a (Ansiedad Rasgo)",
    "37. Algunas ideas poco importantes me rondan la cabeza y me molestan (Ansiedad Rasgo)", "38. Me afectan tanto los desengaños que no puedo olvidarlos (Ansiedad Rasgo)",
    "39. Soy una persona estable (Ansiedad Rasgo)", "40. Cuando pienso en mis asuntos actuales me pongo tenso/a (Ansiedad Rasgo)"
]
OPCIONES_STAI = {
    0: "0 - Nada / Casi nunca",
    1: "1 - Algo / A veces",
    2: "2 - Bastante / A menudo",
    3: "3 - Mucho / Casi siempre"
}

ITEMS_BDI = [
    {"titulo": "1. Tristeza", "opciones": ["0 - No me siento triste.", "1 - Me siento triste gran parte del tiempo.", "2 - Estoy triste todo el tiempo.", "3 - Estoy tan triste o soy tan desdichado que no puedo soportarlo."]},
    {"titulo": "2. Pesimismo", "opciones": ["0 - No me siento desanimado/a respecto al futuro.", "1 - Me siento más desanimado/a respecto al futuro que antes.", "2 - No espero que las cosas mejoren para mí.", "3 - Siento que el futuro es desesperanzador y que las cosas solo empeorarán."]},
    {"titulo": "3. Fracaso", "opciones": ["0 - No me siento como un/a fracasado/a.", "1 - He fracasado más de lo que debería.", "2 - Cuando miro hacia atrás, veo muchos fracasos.", "3 - Siento que como persona soy un fracaso total."]},
    {"titulo": "4. Pérdida de placer", "opciones": ["0 - Obtengo tanto placer como siempre de las cosas que me gustan.", "1 - No disfruto de las cosas tanto como antes.", "2 - Obtengo muy poco placer de las cosas que antes disfrutaba.", "3 - No puedo obtener ningún placer de las cosas que antes disfrutaba."]},
    {"titulo": "5. Sentimientos de culpa", "opciones": ["0 - No me siento particularmente culpable.", "1 - Me siento culpable respecto a varias cosas que he hecho o debería haber hecho.", "2 - Me siento bastante culpable la mayor parte del tiempo.", "3 - Me siento culpable todo el tiempo."]},
    {"titulo": "6. Sentimientos de castigo", "opciones": ["0 - No siento que esté siendo castigado/a.", "1 - Siento que tal vez pueda ser castigado/a.", "2 - Espero ser castigado/a.", "3 - Siento que estoy siendo castigado/a."]},
    {"titulo": "7. Disconformidad con uno mismo", "opciones": ["0 - Siento lo mismo que antes sobre mí mismo/a.", "1 - He perdido la confianza en mí mismo/a.", "2 - Estoy decepcionado/a de mí mismo/a.", "3 - No me gusto en absoluto."]},
    {"titulo": "8. Autocrítica", "opciones": ["0 - No me critico ni me culpo más de lo habitual.", "1 - Estoy más crítico/a conmigo mismo/a de lo que solía estar.", "2 - Me critico a mí mismo/a por todos los errores.", "3 - Me culpo a mí mismo/a por todo lo malo que sucede."]},
    {"titulo": "9. Pensamientos o deseos suicidas", "opciones": ["0 - No tengo ningún pensamiento de matarme.", "1 - Tengo pensamientos de matarme, pero no los llevaría a cabo.", "2 - Me gustaría matarme.", "3 - Me mataría si tuviera la oportunidad."]},
    {"titulo": "10. Llanto", "opciones": ["0 - No lloro más de lo que solía hacerlo.", "1 - Lloro más de lo que solía hacerlo.", "2 - Lloro por cualquier pequeñez.", "3 - Siento ganas de llorar pero no puedo."]},
    {"titulo": "11. Agitación", "opciones": ["0 - No me siento más inquieto/a o agitado/a que de costumbre.", "1 - Me siento más inquieto/a o agitado/a que de costumbre.", "2 - Estoy tan inquieto/a o agitado/a que me cuesta quedarme quieto/a.", "3 - Estoy tan inquieto/a o agitado/a que tengo que estar en constante movimiento."]},
    {"titulo": "12. Pérdida de interés", "opciones": ["0 - No he perdido el interés en otras personas o actividades.", "1 - Estoy menos interesado/a en otras personas o cosas que antes.", "2 - He perdido casi todo el interés en otras personas o cosas.", "3 - Me resulta difícil interesarme por algo."]},
    {"titulo": "13. Indecisión", "opciones": ["0 - Tomo decisiones tan bien como siempre.", "1 - Me resulta más difícil tomar decisiones que de costumbre.", "2 - Tengo mucha más dificultad para tomar decisiones que antes.", "3 - Tengo problemas para tomar cualquier decisión."]},
    {"titulo": "14. Inutilidad", "opciones": ["0 - No me siento inútil.", "1 - No me considero tan valioso/a e útil como solía ser.", "2 - Me siento más inútil en comparación con otras personas.", "3 - Me siento totalmente inútil."]},
    {"titulo": "15. Pérdida de energía", "opciones": ["0 - Tengo tanta energía como siempre.", "1 - Tengo menos energía de la que solía tener.", "2 - No tengo suficiente energía para hacer casi nada.", "3 - No tengo energía para hacer nada."]},
    {"titulo": "16. Cambios en el patrón de sueño", "opciones": ["0 - No he experimentado ningún cambio en mi patrón de sueño.", "1 - Duermo algo más o algo menos que de costumbre.", "2 - Duermo mucho más o mucho menos que de costumbre.", "3 - Duermo la mayor parte del tiempo o me despierto 1-2 horas antes y no puedo volver a dormirme."]},
    {"titulo": "17. Irritabilidad", "opciones": ["0 - No estoy más irritable de lo habitual.", "1 - Estoy más irritable de lo habitual.", "2 - Estoy mucho más irritable de lo habitual.", "3 - Estoy irritable todo el tiempo."]},
    {"titulo": "18. Cambios en el apetito", "opciones": ["0 - No he experimentado ningún cambio en mi apetito.", "1 - Mi apetito es algo menor o mayor que de costumbre.", "2 - Mi apetito es mucho menor o mayor que de costumbre.", "3 - No tengo apetito en absoluto o tengo ansias de comer todo el tiempo."]},
    {"titulo": "19. Dificultad de concentración", "opciones": ["0 - Puedo concentrarme tan bien como siempre.", "1 - No puedo concentrarme tan bien como habitualmente.", "2 - Me cuesta mantener la concentración en cualquier cosa por mucho tiempo.", "3 - Encuentro que no puedo concentrarme en nada."]},
    {"titulo": "20. Cansancio o fatiga", "opciones": ["0 - No estoy más cansado/a o fatigado/a que de costumbre.", "1 - Me canso o fatigo más fácilmente que de costumbre.", "2 - Estoy demasiado cansado/a o fatigado/a para hacer muchas de las cosas que solía hacer.", "3 - Estoy demasiado cansado/a o fatigado/a para hacer la mayoría de las cosas que solía hacer."]},
    {"titulo": "21. Pérdida de interés en el sexo", "opciones": ["0 - No he notado ningún cambio reciente en mi interés por el sexo.", "1 - Estoy menos interesado/a en el sexo de lo que solía estar.", "2 - Estoy mucho menos interesado/a en el sexo ahora.", "3 - He perdido el interés en el sexo por completo."]}
]

# Banco completo y oficial de los 344 reactivos reales del PAI (TEA Ediciones)
ITEMS_PAI = [
    "1. Mis amigos están disponibles cuando los necesito.",
    "2. Tengo algunos conflictos internos que me causan problemas.",
    "3. Mi salud ha limitado algunas de mis actividades.",
    "4. En algunas ocasiones siento tanta tensión que me cuesta mucho soportarlo.",
    "5. A veces necesito hacer las cosas de una cierta forma para evitar ponerme nervioso.",
    "6. Estoy triste gran parte del tiempo sin que haya una razón para ello.",
    "7. Con frecuencia pienso y hablo tan deprisa que los demás no pueden seguir mi pensamiento.",
    "8. La mayor parte de la gente que conozco es digna de confianza.",
    "9. De vez en cuando pierdo completamente la memoria.",
    "10. Tengo algunas ideas que los demás consideran extrañas.",
    "11. He dañado intencionadamente algunas pertenencias de otras personas.",
    "12. Mi salud es muy buena para mi edad.",
    "13. Soy una persona muy sociable.",
    "14. Tengo cambios de humor repentinos.",
    "15. A veces me siento culpable por la cantidad de alcohol que bebo.",
    "16. Me encuentro a gusto en las situaciones en las que tengo que dirigir a otros.",
    "17. A menudo cambio la imagen y la idea que tengo sobre mí.",
    "18. Tengo bastante mal carácter.",
    "19. He tenido algunas relaciones tormentosas.",
    "20. En ciertas ocasiones me gustaría estar muerto.",
    "21. La gente tiene miedo de mi temperamento.",
    "22. A veces tomo drogas para sentirme mejor.",
    "23. He probado casi todos los tipos de drogas.",
    "24. A veces incluso las cosas pequeñas me preocupan demasiado.",
    "25. Suelo tener dificultad para concentrarme a causa de mis nervios.",
    "26. Con frecuencia tengo miedo de 'meter la pata' y decir algo inconveniente.",
    "27. Siento que he decepcionado a todo el mundo.",
    "28. Tengo muchas ideas brillantes.",
    "29. Hay personas que quieren hacerme daño.",
    "30. Me parece que no me relaciono bien con la gente.",
    "31. He pedido dinero prestado a sabiendas de que no podría devolverlo.",
    "32. La mayor parte del tiempo no me encuentro bien.",
    "33. Con frecuencia me siento inquieto.",
    "34. Sigo reviviendo algo horrible que me ocurrió.",
    "35. Casi no tengo energía.",
    "36. Me enfado cuando otras personas son demasiado lentas para entender mis ideas.",
    "37. La gente suele tratarme bastante bien.",
    "38. Mis pensamientos se han hecho bastante confusos.",
    "39. Disfruto haciendo cosas peligrosas.",
    "40. Mi poeta favorito es Ruperto Miralles.",
    "41. La mayor parte de las personas de mi entorno están cuando las necesito.",
    "42. Necesito hacer algunos cambios importantes en mi vida.",
    "43. He tenido algunas enfermedades que los médicos no han sido capaces de explicar.",
    "44. Mi nerviosismo me impide hacer algunas cosas bien.",
    "45. Tengo ciertos impulsos que lucho por controlar.",
    "46. He olvidado lo que es sentirse feliz.",
    "47. Asumo tantos compromisos que luego no soy capaz de cumplirlos.",
    "48. Debo estar alerta ante la posibilidad de que algunas personas no sean leales.",
    "49. No tengo casi ningún buen recuerdo de mi infancia.",
    "50. A veces otras personas meten ideas en mi cabeza.",
    "51. He realizado cosas que no eran completamente legales.",
    "52. Mis problemas de salud son muy complicados.",
    "53. Me resulta fácil hacer nuevos amigos.",
    "54. Experimento estados de ánimo muy intensos.",
    "55. Tengo algunas dificultades para controlar la cantidad de alcohol que bebo.",
    "56. Suelo actuar como un líder de forma natural.",
    "57. A veces tengo una intensa sensación de vacío interior.",
    "58. Nunca tengo problemas por culpa de mi temperamento.",
    "59. Quiero que algunas personas sepan que me han hecho mucho daño.",
    "60. He pensado en algunas formas de quitarme la vida.",
    "61. A veces exploto y pierdo completamente el control sobre mí.",
    "62. Algunas personas me han dicho que tengo problemas con las drogas.",
    "63. El consumo de drogas me ha producido algunos problemas de salud.",
    "64. No acepto bien las críticas.",
    "65. Con frecuencia me resulta difícil divertirme porque todo me preocupa.",
    "66. Tengo temores excesivamente grandes.",
    "67. A veces pienso que no valgo nada.",
    "68. Tengo muchas cualidades interesantes de las que otras personas carecen.",
    "69. Algunas personas hacen cosas para que yo quede mal.",
    "70. Tengo muy poco que decir a otras personas.",
    "71. Me aprovecharía de los demás si lo tuviera fácil.",
    "72. Tengo muchos dolores.",
    "73. Algunas veces me preocupo tanto que me parece que voy a desmayarme.",
    "74. Con frecuencia me vienen recuerdos del pasado que me provocan malestar.",
    "75. Concilio fácilmente el sueño.",
    "76. No tengo paciencia con la gente que intenta frenarme.",
    "77. Creo que en mi vida he tenido tanta suerte como la mayor parte de la gente.",
    "78. Algunas veces mezclo unos pensamientos con otros.",
    "79. Hago muchas cosas peligrosas sólo por la emoción que me producen.",
    "80. A veces recibo por correo anuncios que no me interesan en absoluto.",
    "81. Cuando tengo problemas cuento con personas con las que puedo hablar.",
    "82. Tengo que cambiar en algunos aspectos, aunque me cueste mucho.",
    "83. Alguna parte de mi cuerpo se ha quedado insensible en ocasiones, sin saber por qué.",
    "84. En algunas ocasiones tengo miedo sin que haya motivos para ello.",
    "85. Me incomoda que las cosas no estén en su sitio.",
    "86. Cualquier cosa me supone un gran esfuerzo.",
    "87. Mis amigos no son capaces de seguir todas mis actividades sociales.",
    "88. La mayor parte de la gente tiene buenas intenciones.",
    "89. Mi destino ha sido ser infeliz desde el día en que nací.",
    "90. A veces parece que mis pensamientos se producen en voz alta y que los demás pueden oírlos.",
    "91. He dicho muchas mentiras para librarme de situaciones comprometidas.",
    "92. Me cuesta mucho hacer las cosas por los problemas de salud que tengo.",
    "93. Me gusta conocer a nuevas personas.",
    "94. A veces me meto en problemas porque actúo de forma muy impulsiva.",
    "95. Algunas personas cercanas piensan que bebo demasiado.",
    "96. Se me dan bien los trabajos en los que hay que dirigir a otros.",
    "97. Me preocupa mucho que otras personas puedan abandonarme.",
    "98. Cuando estoy conduciendo y me indigno con otros conductores hago que se den cuenta de ello.",
    "99. Algunas personas muy próximas me han abandonado.",
    "100. He hecho planes para matarme.",
    "101. Cuando me enfurezco es muy difícil calmarme.",
    "102. He tenido problemas económicos por el consumo de drogas.",
    "103. Soy incapaz de controlar mi consumo de drogas.",
    "104. A veces me quejo demasiado.",
    "105. Con frecuencia siento tal preocupación y nerviosismo que casi no puedo soportarlo.",
    "106. Cuando tengo que hacer algo delante de otras personas siento muchos nervios.",
    "107. Me siento sin fuerzas para continuar.",
    "108. Tengo planes que me convertirán algún día en una persona famosa.",
    "109. Las personas que me rodean son leales conmigo.",
    "110. Soy una persona solitaria.",
    "111. Haría cualquier cosa si me pagasen lo suficiente.",
    "112. Tengo buena salud.",
    "113. A veces siento mareos cuando he estado sometido a una presión fuerte.",
    "114. El recuerdo de una mala experiencia me ha afectado durante mucho tiempo.",
    "115. Es raro que tenga alguna dificultad para dormir.",
    "116. A veces me irrito porque otras personas no comprenden mis planes.",
    "117. He dado mucho pero es poco lo que he recibido a cambio.",
    "118. Algunas veces me cuesta separar unos pensamientos de otros.",
    "119. A veces me comporto de forma desenfrenada e insensata.",
    "120. El deporte que más me gusta ver por televisión es el salto de altura.",
    "121. Las personas que conozco se preocupan por mí.",
    "122. Necesito ayuda para afrontar los problemas importantes.",
    "123. En alguna ocasión mis piernas estaban tan débiles que no podía caminar.",
    "124. A menudo tengo la sensación de que está a punto de ocurrir algo horrible.",
    "125. Soy capaz de descansar aunque mi casa esté desordenada.",
    "126. Parece que nada es capaz de proporcionarme placer.",
    "127. En ocasiones mis pensamientos se mueven a una velocidad excesiva.",
    "128. La gente suele ocultar sus verdaderas intenciones.",
    "129. Tengo problemas psicológicos graves que comenzaron de forma repentina.",
    "130. Hay personas que intentan controlar mis pensamientos.",
    "131. Nunca he tenido conflictos con la ley.",
    "132. Parece que mis problemas de salud son siempre difíciles de tratar.",
    "133. Soy una persona acogedora.",
    "134. A veces no puedo contener mi rabia.",
    "135. Mi costumbre de beber me ha producido algunos problemas en las relaciones con los demás.",
    "136. Me cuesta mucho defenderme sin ayuda.",
    "137. A menudo me pregunto lo que debería hacer con mi vida.",
    "138. Sería capaz de gritar a otros con tal de que queden claros mis argumentos.",
    "139. Cuando estoy muy enfadado suelo hacer cosas para hacerme daño.",
    "140. En los últimos tiempos he estado pensando en el suicidio.",
    "141. A veces rompo cosas cuando estoy muy furioso.",
    "142. Nunca consumo drogas ilegales.",
    "143. Me perjudica mi comportamiento excesivamente impulsivo.",
    "144. A veces soy demasiado impaciente.",
    "145. Mis amigos dicen que me preocupo demasiado.",
    "146. Rara vez siento miedo.",
    "147. Por más que lo intente, nada me sale bien.",
    "148. Creo que tengo las respuestas a algunas preguntas importantes.",
    "149. Algunas personas tratan de impedir que yo pueda progresar.",
    "150. Hay pocas personas a las que sienta cercanas.",
    "151. Pienso en mí ante todo y dejo que los demás cuiden de sí mismos.",
    "152. Rara vez me quejo de mi estado de salud.",
    "153. A veces me cuesta respirar cuando me someto a mucha tensión.",
    "154. Parece que no puedo librarme de ciertos acontecimientos del pasado.",
    "155. He estado moviéndome con más lentitud de lo normal.",
    "156. Tengo planes importantes y me molesta mucho que otras personas intenten meterse en medio.",
    "157. Muchas personas no son capaces de apreciar lo que he hecho por ellas.",
    "158. A veces parece que alguien está bloqueando mis pensamientos.",
    "159. Me gusta conducir muy deprisa.",
    "160. La mayor parte de la gente está deseando ir al dentista.",
    "161. La gente não comprende lo mucho que sufro.",
    "162. Tengo muchos problemas económicos.",
    "163. Recientemente se han producido muchos cambios en mi vida.",
    "164. En mi casa hay poca estabilidad.",
    "165. Las cosas no van bien en mi familia.",
    "166. He perdido el interés por cosas que antes me gustaban.",
    "167. Últimamente he tenido mucha más energía de la habitual.",
    "168. Generalmente doy por supuesto que la gente dice la verdad.",
    "169. Paso la mayor parte del tiempo en soledad.",
    "170. He oído voces que nadie más es capaz de oír.",
    "171. Me gusta hacer cosas sólo para comprobar si puedo salir impune de ellas.",
    "172. He tenido únicamente los problemas de salud que la mayoría de la gente tiene.",
    "173. Necesito tiempo para sentirme en confianza con personas que no conozco.",
    "174. Siempre he sido una persona bastante feliz.",
    "175. La bebida me ayuda a sobrellevar ciertas situaciones sociales.",
    "176. Soy el tipo de persona que se hace cargo de las cosas.",
    "177. No puedo soportar separarme de las personas que son muy cercanas a mí.",
    "178. Nunca pierdo el control por estar demasiado furioso.",
    "179. He cometido algunos errores graves en relación con las personas que he elegido como amigas.",
    "180. Durante mucho tiempo he estado pensando en el suicidio.",
    "181. He amenazado a otras personas con hacerlas daño.",
    "182. He utilizado medicamentos para animarme.",
    "183. Suelo tener pocos cambios de humor.",
    "184. A veces intento evitar a las personas que me disgustan.",
    "185. Mi preocupación por las cosas es similar a la de la mayoría de las personas.",
    "186. No me asusta conducir por autopistas.",
    "187. Me parece que me cuesta mucho concentrarme.",
    "188. He tenido algunos éxitos destacados.",
    "189. Algunas personas cambian sus planes para molestarme.",
    "190. Disfruto con la compañía de otras personas.",
    "191. No me gusta sentirme ligado a otra persona.",
    "192. Tengo problemas de espalda.",
    "193. Soy capaz de relajarme con facilidad.",
    "194. He tenido algunas experiencias terribles que hacen que me sienta culpable.",
    "195. Con frecuencia me despierto muy temprano por la mañana y luego no puedo volver a dormirme.",
    "196. Puedo ser muy exigente cuando quiero que las cosas se hagan deprisa.",
    "197. Generalmente se ha reconocido lo que he hecho.",
    "198. Mi mente tiende a saltar rápidamente de unas cosas a otras.",
    "199. La idea de una vida tranquila y ordenada nunca me ha interesado.",
    "200. Mis aficiones favoritas son el tiro con arco y la filatelia.",
    "201. Me gusta estar con mi familia.",
    "202. Me gusta cómo soy.",
    "203. En ciertas ocasiones he perdido la sensibilidad en las manos.",
    "204. Raras veces siento tensión o ansiedad.",
    "205. Normalmente me doy cuenta de cuando algo tiene muchos gérmenes.",
    "206. No me interesa la vida.",
    "207. Tengo la sensación de que necesito estar en constante actividad, sin descansar.",
    "208. La gente piensa que soy demasiado suspicaz.",
    "209. A veces no puedo recordar quién soy.",
    "210. Otras personas pueden leer mis pensamientos.",
    "211. Nunca me expulsaron de la escuela durante mi niñez, ni siquiera temporalmente.",
    "212. He tenido algunas enfermedades o molestias bastante raras.",
    "213. Se necesita tiempo para que otras personas lleguen a conocerme.",
    "214. En algunas ocasiones me he enfurecido tanto que era incapaz de manifestar toda la ira que sentía.",
    "215. En ocasiones he tenido que dejar la bebida.",
    "216. Prefiero que sean otros los que toman las decisiones.",
    "217. Normalmente no me aburro.",
    "218. Siempre que puedo evito las discusiones.",
    "219. Cuando tengo un amigo o amiga, lo es para mucho tiempo.",
    "220. La muerte sería un alivio.",
    "221. La gente piensa que soy una persona agresiva.",
    "222. Nunca consumo drogas para ayudarme a enfrentarme al mundo.",
    "223. Rara vez me siento una persona solitaria.",
    "224. A veces dejo las cosas para el último momento.",
    "225. Generalmente me preocupo por las cosas más de lo que debería.",
    "226. No me asustan las alturas.",
    "227. Creo que en el futuro me van a ocurrir cosas favorables.",
    "228. Creo que podría ser un buen cómico.",
    "229. Es muy raro que la gente me trate mal a propósito.",
    "230. Siempre que puedo me gusta estar con otras personas.",
    "231. No me gusta mantener una relación durante mucho tiempo.",
    "232. Tengo problemas de estómago.",
    "233. A veces noto que mi corazón late muy fuerte.",
    "234. Sigo teniendo pesadillas sobre el pasado.",
    "235. Tengo buen apetito.",
    "236. Me molesta mucho si alguna persona trata de impedir que cumpla mis objetivos.",
    "237. La gente que ha tenido éxito generalmente lo ha merecido.",
    "238. A veces me parece que me han robado los pensamientos.",
    "239. Cuando me canso de un sitio inmediatamente me voy a otro.",
    "240. No me gusta comprar cosas que me parecen excesivamente caras.",
    "241. En mi familia discutimos más que hablamos.",
    "242. Muchos de mis problemas son consecuencia de mi actitud.",
    "243. He tenido experiencias de visión doble o de visión borrosa.",
    "244. Me sobresalto con facilidad.",
    "245. Los demás consideran que presto mucha atención a los detalles.",
    "246. En los últimos tiempos me he sentido feliz habitualmente.",
    "247. Últimamente tengo menos necesidad de dormir de la habitual.",
    "248. Generalmente las cosas no son lo que aparentan a primera vista.",
    "249. A veces veo sólo en blanco y negro.",
    "250. Tengo un sexto sentido que me avisa de las cosas que van a ocurrir.",
    "251. Generalmente me portaba bien cuando iba al colegio.",
    "252. He ido muchas veces al médico en mi vida.",
    "253. Intento acoger a las personas que parecen estar solas.",
    "254. A veces tomo una copa de una bebida alcohólica nada más levantarme.",
    "255. La bebida me ha causado algunos problemas en casa.",
    "256. Digo siempre lo que pienso.",
    "257. Suelo hacer lo que otras personas quieren que haga.",
    "258. A veces puedo ser una persona muy violenta.",
    "259. Es muy difícil hacer que me enfade.",
    "260. He estado pensando en lo qué podría decir en una carta de suicidio.",
    "261. No tengo motivos para seguir viviendo.",
    "262. Nunca he tenido problemas en el trabajo por causa de las drogas.",
    "263. Gasto el dinero con demasiada facilidad.",
    "264. A veces hago promesas que no puedo cumplir.",
    "265. A veces me pongo tan nervioso que me parece que voy a morir.",
    "266. Evito montarme en aviones.",
    "267. Tengo cosas importantes que aportar.",
    "268. Últimamente confío tanto en mí que creo que puedo conseguir lo que me proponga.",
    "269. La gente me tiene manía.",
    "270. Hago amigos con facilidad.",
    "271. Siempre tengo algo que decir u opinar sobre cualquier cosa.",
    "272. Me duele la cabeza con más frecuencia que a la mayor parte de la gente.",
    "273. Me sudan las manos con frecuencia.",
    "274. Tuve una experiencia muy mala que me ha hecho perder el interés por algunas cosas con las que antes disfrutaba.",
    "275. A menudo me despierto a mitad de la noche.",
    "276. A veces estoy muy suspicaz y me enfado con facilidad.",
    "277. No soy una persona que suela guardar rencor.",
    "278. Los pensamientos desaparecen rápidamente de mi mente.",
    "279. Nunca tomo riesgos si puedo evitarlo.",
    "280. La mayor parte de la gente prefiere ganar a perder.",
    "281. Paso poco tiempo con mi familia.",
    "282. Soy capaz de resolver mis problemas por mi cuenta.",
    "283. Algunas partes de mi cuerpo han quedado paralizadas en alguna ocasión.",
    "284. No soy de las personas que se asustan fácilmente.",
    "285. Me controlo de una forma muy estricta.",
    "286. Casi siempre soy una persona alegre y positiva.",
    "287. Casi nunca compro cosas por un impulso repentino.",
    "288. La gente tiene que ganarse mi confianza.",
    "289. Tengo visiones en las que me veo en la obligación de cometer ciertos delitos.",
    "290. No creo que existan personas capaces de leer la mente.",
    "291. Nunca he robado dinero u objetos de otras personas.",
    "292. Me gusta hablar con otras personas sobre sus problemas de salud.",
    "293. Soy una persona afectuosa.",
    "294. Nunca conduzco si he estado bebiendo.",
    "295. Casi nunca bebo alcohol.",
    "296. La gente suele pedirme opinión.",
    "297. Si cuando acudo a un establecimiento me atienden mal reclamo al responsable.",
    "298. Regaño a las personas que se lo merecen.",
    "299. Trato de evitar el tener que elevar la voz.",
    "300. Me he preguntado cómo reaccionarían otras personas si me suicidase.",
    "301. Tengo muchos motivos para vivir.",
    "302. Comparto el consumo de drogas con mis mejores amigos.",
    "303. Soy una persona temeraria.",
    "304. A veces podría haber actuado más reflexivamente de lo que lo hice.",
    "305. No me preocupo por las cosas que escapan a mi control.",
    "306. No me preocupa viajar en autobús o en tren.",
    "307. Tengo bastante éxito en lo que emprendo.",
    "308. Soy incapaz de verme como una persona famosa.",
    "309. Soy objeto de una conspiración.",
    "310. Mantengo el contacto con mis amigos y amigas.",
    "311. Cuando hago una promesa no siento la necesidad de cumplirla.",
    "312. Tengo diarreas con frecuencia.",
    "313. Tengo el pulso firme.",
    "314. Evito ciertas cosas que me traen malos recuerdos.",
    "315. Tengo poco interés por el sexo.",
    "316. Soy poco paciente con la gente que no está de acuerdo con mis planes.",
    "317. A la larga uno siempre se ve recompensado si ayuda a los demás.",
    "318. Soy capaz de concentrarme ahora tan bien como en mis mejores tiempos.",
    "319. No soy del tipo de personas a las que asustan los retos.",
    "320. En mi tiempo libre suelo leer, ver la televisión o simplemente descansar.",
    "321. Me gustaría entender por qué actúo en la forma en que lo hago.",
    "322. Mi vida es completamente impredecible.",
    "323. En algunas ocasiones mi vista ha empeorado y luego ha vuelto a mejorar.",
    "324. Soy una persona muy tranquila y relajada.",
    "325. La gente dice que soy perfeccionista.",
    "326. Me satisface plenamente mi situación laboral.",
    "327. Me preocupa no tener bastante dinero para salir adelante.",
    "328. La relación con mi pareja no va bien.",
    "329. Creo que dentro de mí hay tres o cuatro personalidades completamente diferentes.",
    "330. Soy una persona bastante comprensiva.",
    "331. Es importante para mí tener relaciones personales íntimas.",
    "332. Tengo poca paciencia con la gente.",
    "333. Tengo más amigos que la mayor parte de la gente que conozco.",
    "334. Nunca he tenido problemas por haber bebido.",
    "335. He tenido algunos problemas en el trabajo por culpa de la bebida.",
    "336. Suelo intentar que los demás no se den cuenta cuando discrepo de ellos.",
    "337. Soy una persona muy independiente.",
    "338. La gente se sorprendería si me viese gritar a alguien.",
    "339. Desde que soy una persona adulta nunca he empezado una pelea que haya llegado a las manos.",
    "340. Estoy pensando en la posibilidad de suicidarme.",
    "341. Las cosas nunca me han ido tan mal como para pensar en suicidarme.",
    "342. El consumo de drogas nunca me ha producido problemas con la familia o los amigos.",
    "343. Pongo mucho cuidado en la forma de gastar el dinero.",
    "344. Casi nunca estoy de mal humor."
]

OPCIONES_PAI = {
    "F": "F - Falso",
    "LV": "LV - Ligeramente verdadero",
    "BV": "BV - Bastante verdadero",
    "CV": "CV - Completamente verdadero"
}

MAPA_TESTS = {
    "LSB-50": {"items": ITEMS_LSB50, "opciones": OPCIONES_LSB50},
    "MMPI-2-RF": {"items": ITEMS_MMPI2RF, "opciones": None},
    "CUIDA": {"items": ITEMS_CUIDA, "opciones": OPCIONES_CUIDA},
    "STAI": {"items": ITEMS_STAI, "opciones": OPCIONES_STAI},
    "BDI-II": {"items": [item["titulo"] for item in ITEMS_BDI], "opciones": None},
    "PAI": {"items": ITEMS_PAI, "opciones": OPCIONES_PAI}
}

# -----------------------------------------------------------------------------
# DETECCIÓN DE PARÁMETROS URL (Link automático para el evaluado)
# -----------------------------------------------------------------------------
query_params = st.query_params
token_url = query_params.get("token", None)

if token_url and "token_activo" not in st.session_state:
    token_limpio = token_url.strip().upper()
    datos_actuales = cargar_datos_db()
    if token_limpio in datos_actuales:
        if datos_actuales[token_limpio].get("estado") == "finalizado":
            st.error("Este enlace ya ha sido utilizado y finalizado. No puede volver a ingresar.")
        else:
            st.session_state["token_activo"] = token_limpio
            st.query_params.clear()

# -----------------------------------------------------------------------------
# 3. BARRA LATERAL RESTRICTORA (ACCESO PRIVADO AL PERITO)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.title("🔒 Acceso Profesional")
    
    if not st.session_state["perito_autenticado"]:
        with st.expander("🔑 Iniciar Sesión Perito"):
            pass_input = st.text_input("Contraseña Maestra:", type="password", key="input_pass_perito", autocomplete="off")
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
    st.write("Bienvenido al módulo pericial de gestión de evaluaciones y cadena de custodia.")
    st.divider()
    
    st.subheader("🔑 Generar Clave y Link de Acceso")
    st.write("Haga clic en el botón para crear un código y un enlace directo para el evaluado:")
    
    if st.button("🎲 Generar Nueva Clave y Link", type="primary"):
        nueva_clave = generar_token_unico()
        ip_perito, ua_perito = obtener_metadatos_conexion()
        info_nueva = {
            "estado": "activa",
            "datos_persona": None,
            "evaluaciones": {},
            "ip_acceso": ip_perito,
            "user_agent": ua_perito
        }
        guardar_token_db(nueva_clave, info_nueva)
        
        st.success(f"¡Clave generada con éxito!: **`{nueva_clave}`**")
        
        base_url = "https://psi-forense-hwgpyudkkkwqfwsjx2kkge.streamlit.app"
        link_completo = f"{base_url}/?token={nueva_clave}"
        
        st.markdown(f"🔗 **Link directo para enviar por WhatsApp o correo:**")
        st.code(link_completo, language="text")
        st.info("Copie este enlace y envíatelo al evaluado. Al hacer clic, ingresará automáticamente.")
    
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
                    nombre_str = persona['nombre'] if persona else "Desconocido"
                    st.markdown(f"🔒 **Clave:** `{clave}` | **Estado:** Finalizado ({nombre_str})")
                elif not evals and not persona:
                    st.markdown(f"🟢 **Clave:** `{clave}` | **Estado:** Disponible")
                elif not evals:
                    info_persona = f" ({persona['nombre']})" if persona else ""
                    st.markdown(f"🟢 **Clave:** `{clave}` | **Estado:** En proceso{info_persona}")
                else:
                    nombre_str = persona['nombre'] if persona else "Desconocido"
                    tests_realizados = ", ".join(list(evals.keys()))
                    st.markdown(f"🔴 **Clave:** `{clave}` | **Eval:** {nombre_str} | **Pruebas:** {tests_realizados}")
            
            with col_btn_ver:
                if persona:
                    if f"modal_ver_{clave}" not in st.session_state:
                        st.session_state[f"modal_ver_{clave}"] = False
                    
                    btn_label = "👁️ Ocultar" if st.session_state[f"modal_ver_{clave}"] else "👁️ Ver Protocolo" if evals else "👤 Ver Datos"
                    
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
                        st.write(f"**Fecha y Hora (Buenos Aires):** {persona.get('fecha', 'N/A')} - {persona.get('hora', 'N/A')} hs")
                        st.write(f"**Hash de Identidad:** `{persona.get('hash_identidad', 'N/A')}`")
                    else:
                        st.warning("El evaluado aún no ha completado sus datos filiatorios.")
                    
                    st.write(f"**Dirección IP de Acceso:** `{info.get('ip_acceso', 'N/A')}`")
                    st.write(f"**Dispositivo (User-Agent):** `{info.get('user_agent', 'N/A')}`")
                    st.write(f"**Hash del Bloque (Inalterabilidad):** `{info.get('hash_bloque', 'N/A')}`")
                    
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
                                        "Respuesta": respuesta_texto
                                    })
                                st.dataframe(tabla_datos, key=f"df_{clave}_{test_nombre}", use_container_width=True, hide_index=True)
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
        st.write("Por favor, ingrese el **código de acceso** o utilice el enlace directo que le envió el profesional:")
        
        clave_ingresada = st.text_input("Código asignado:", key="input_codigo_evaluado_unico", placeholder="Ej: EVAL-SS4BJQ", autocomplete="off")
        
        if st.button("Ingresar", use_container_width=True):
            clave_limpia = clave_ingresada.strip().upper()
            if clave_limpia in claves_globales:
                estado_token = claves_globales[clave_limpia].get("estado", "activa")
                if estado_token == "finalizado":
                    st.error("Este token ya ha sido utilizado y finalizado. No puede volver a ingresar.")
                else:
                    st.session_state["token_activo"] = clave_limpia
                    st.session_state["test_enviado"] = False
                    st.rerun()
            else:
                st.error("Código inválido o inexistente. Verifique el código ingresado con el evaluador.")
    
    else:
        token_actual = st.session_state["token_activo"]
        claves_globales = cargar_datos_db()
        datos_token = claves_globales.get(token_actual, {"estado": "activa", "datos_persona": None, "evaluaciones": {}})
        
        if datos_token.get("estado") == "finalizado":
            st.error("Este token ya ha sido finalizado. Su sesión ha caducado.")
            if st.button("Aceptar e ir al inicio", use_container_width=True):
                del st.session_state["token_activo"]
                st.rerun()
        else:
            ip_registrada = datos_token.get("ip_acceso")
            if ip_registrada and ip_registrada != "IP_LOCAL_O_NO_DETECTADA" and ip_registrada != ip_cliente:
                st.warning("⚠️ **Aviso de seguridad forense:** Se detecta variación en la red de conexión respecto a la emisión inicial del token. Esta incidencia queda registrada para control de cadena de custodia.")

            if datos_token.get("datos_persona") is None:
                st.subheader("Datos del Evaluado y Registro de Identidad")
                st.write("Por favor, complete sus datos filiatorios antes de acceder a las escalas:")
                
                with st.form("form_datos_personales"):
                    nombre_comp = st.text_input("Nombre y Apellido completo:", autocomplete="off")
                    dni_val = st.text_input("Número de DNI / Documento:", autocomplete="off")
                    
                    guardar_datos = st.form_submit_button("Generar Hash de Identidad y Acceder", use_container_width=True)
                    
                    if guardar_datos:
                        if nombre_comp.strip() != "" and dni_val.strip() != "":
                            try:
                                tz_ba = ZoneInfo("America/Argentina/Buenos_Aires")
                                ahora_ba = datetime.now(tz_ba)
                            except Exception:
                                tz_ba = timezone(timedelta(hours=-3))
                                ahora_ba = datetime.now(tz_ba)
                            
                            fecha_eval = ahora_ba.strftime("%Y-%m-%d")
                            hora_eval = ahora_ba.strftime("%H:%M:%S")
                            
                            str_para_hash = f"{token_actual}-{nombre_comp.strip()}-{dni_val.strip()}-{fecha_eval}-{hora_eval}-{ip_cliente}"
                            hash_generado = hashlib.sha256(str_para_hash.encode('utf-8')).hexdigest()
                            
                            datos_token["datos_persona"] = {
                                "nombre": nombre_comp.strip(),
                                "dni": dni_val.strip(),
                                "fecha": fecha_eval,
                                "hora": hora_eval,
                                "hash_identidad": hash_generado
                            }
                            datos_token["ip_acceso"] = ip_cliente
                            datos_token["user_agent"] = ua_cliente
                            
                            guardar_token_db(token_actual, datos_token)
                            st.rerun()
                        else:
                            st.warning("Por favor complete sus Nombre, Apellido y DNI para poder avanzar.")
            
            else:
                persona = datos_token["datos_persona"]
                hora_str = persona.get("hora", "N/A")
                evaluaciones_realizadas = datos_token.get("evaluaciones", {})
                
                st.info(f"Evaluado: **{persona['nombre']}** | DNI: **{persona['dni']}** | Hora (BA): **{hora_str}** | Hash Identidad: `{persona['hash_identidad'][:10]}...`")

                if st.session_state.get("test_enviado"):
                    st.success("¡Escala enviada y registrada bajo cadena de custodia digital inalterable!")
                    st.write("Sus respuestas han sido almacenadas de manera segura para el perito.")
                    st.divider()
                    if st.button("🏠 Completar otra escala / Volver al menú", type="primary", use_container_width=True):
                        st.session_state["test_enviado"] = False
                        st.rerun()
                else:
                    if evaluaciones_realizadas:
                        st.write("✅ **Escalas completadas hasta el momento:** " + ", ".join(list(evaluaciones_realizadas.keys())))
                    
                    test_seleccionado = st.selectbox(
                        "Seleccione la escala a completar:",
                        [
                            "-- Seleccione una opción --", 
                            "Listado de Síntomas Breve (LSB-50)", 
                            "MMPI-2-RF (Inventario Multifásico de Personalidad)",
                            "CUIDA (Evaluación de Adoptantes, Cuidadores, Tutores y Mediadores)",
                            "STAI (Cuestionario de Ansiedad Estado-Rasgo)",
                            "BDI-II (Inventario de Depresión de Beck)",
                            "PAI (Inventario de Evaluación de la Personalidad)"
                        ]
                    )
                    
                    # A) LSB-50
                    if test_seleccionado == "Listado de Síntomas Breve (LSB-50)":
                        st.subheader("Listado de Síntomas Breve (LSB-50)")
                        st.info("""
                        **Instrucciones oficiales:**
                        A continuación se presenta una lista de molestias, problemas o síntomas psicológicos y físicos. Lea cada uno detenidamente y señale hasta qué punto le ha preocupado o molestado **DURANTE LAS ÚLTIMAS DOS SEMANAS, INCLUYENDO EL DÍA DE HOY**.
                        * **0** = Nada | **1** = Algo | **2** = Moderadamente | **3** = Bastante | **4** = Mucho
                        """)
                        respuestas_lsb = {}
                        with st.form("form_lsb50"):
                            for idx, preg in enumerate(ITEMS_LSB50, 1):
                                respuestas_lsb[f"p_{idx}"] = st.radio(
                                    preg, options=list(OPCIONES_LSB50.keys()),
                                    format_func=lambda x: OPCIONES_LSB50[x], horizontal=True, key=f"lsb_{idx}"
                                )
                                st.divider()
                            if st.form_submit_button("Finalizar y Enviar LSB-50", use_container_width=True):
                                datos_token["evaluaciones"]["LSB-50"] = respuestas_lsb
                                datos_token["estado"] = "finalizado"
                                guardar_token_db(token_actual, datos_token)
                                st.session_state["test_enviado"] = True
                                st.rerun()

                    # B) MMPI-2-RF
                    elif test_seleccionado == "MMPI-2-RF (Inventario Multifásico de Personalidad)":
                        st.subheader("MMPI-2-RF")
                        st.info("Marque **Verdadero** o **Falso** según corresponda a su caso habitual.")
                        respuestas_mmpi = {}
                        with st.form("form_mmpi2rf"):
                            for idx, preg in enumerate(ITEMS_MMPI2RF, 1):
                                respuestas_mmpi[f"p_{idx}"] = st.radio(
                                    preg, options=OPCIONES_MMPI, horizontal=True, key=f"mmpi_{idx}"
                                )
                                st.divider()
                            if st.form_submit_button("Finalizar y Enviar MMPI-2-RF", use_container_width=True):
                                datos_token["evaluaciones"]["MMPI-2-RF"] = respuestas_mmpi
                                datos_token["estado"] = "finalizado"
                                guardar_token_db(token_actual, datos_token)
                                st.session_state["test_enviado"] = True
                                st.rerun()

                    # C) CUIDA
                    elif test_seleccionado == "CUIDA (Evaluación de Adoptantes, Cuidadores, Tutores y Mediadores)":
                        st.subheader("Cuestionario CUIDA")
                        st.info("Elija la alternativa de 1 a 4 según su grado de acuerdo.")
                        respuestas_cuida = {}
                        with st.form("form_cuida"):
                            for idx, preg in enumerate(ITEMS_CUIDA, 1):
                                respuestas_cuida[f"p_{idx}"] = st.radio(
                                    preg, options=list(OPCIONES_CUIDA.keys()),
                                    format_func=lambda x: OPCIONES_CUIDA[x], horizontal=True, key=f"cuida_{idx}"
                                )
                                st.divider()
                            if st.form_submit_button("Finalizar y Enviar CUIDA", use_container_width=True):
                                datos_token["evaluaciones"]["CUIDA"] = respuestas_cuida
                                datos_token["estado"] = "finalizado"
                                guardar_token_db(token_actual, datos_token)
                                st.session_state["test_enviado"] = True
                                st.rerun()

                    # D) STAI
                    elif test_seleccionado == "STAI (Cuestionario de Ansiedad Estado-Rasgo)":
                        st.subheader("STAI - Cuestionario de Ansiedad Estado-Rasgo")
                        st.info("Ítems 1-20 (Estado - Ahora mismo) | Ítems 21-40 (Rasgo - En general)")
                        respuestas_stai = {}
                        with st.form("form_stai"):
                            for idx, preg in enumerate(ITEMS_STAI, 1):
                                respuestas_stai[f"p_{idx}"] = st.radio(
                                    preg, options=list(OPCIONES_STAI.keys()),
                                    format_func=lambda x: OPCIONES_STAI[x], horizontal=True, key=f"stai_{idx}"
                                )
                                st.divider()
                            if st.form_submit_button("Finalizar y Enviar STAI", use_container_width=True):
                                datos_token["evaluaciones"]["STAI"] = respuestas_stai
                                datos_token["estado"] = "finalizado"
                                guardar_token_db(token_actual, datos_token)
                                st.session_state["test_enviado"] = True
                                st.rerun()

                    # E) BDI-II
                    elif test_seleccionado == "BDI-II (Inventario de Depresión de Beck)":
                        st.subheader("BDI-II - Inventario de Depresión de Beck")
                        st.info("Seleccione la frase que mejor describa cómo se ha sentido durante las últimas dos semanas.")
                        respuestas_bdi = {}
                        with st.form("form_bdii"):
                            for idx, item in enumerate(ITEMS_BDI, 1):
                                respuestas_bdi[f"p_{idx}"] = st.radio(
                                    item["titulo"], options=item["opciones"], key=f"bdi_{idx}"
                                )
                                st.divider()
                            if st.form_submit_button("Finalizar y Enviar BDI-II", use_container_width=True):
                                datos_token["evaluaciones"]["BDI-II"] = respuestas_bdi
                                datos_token["estado"] = "finalizado"
                                guardar_token_db(token_actual, datos_token)
                                st.session_state["test_enviado"] = True
                                st.rerun()

                    # F) PAI
                    elif test_seleccionado == "PAI (Inventario de Evaluación de la Personalidad)":
                        st.subheader("PAI - Inventario de Evaluación de la Personalidad")
                        st.info("""
                        **Instrucciones oficiales (TEA Ediciones):**
                        Para cada afirmación, decida en qué medida describe su forma de ser, sus pensamientos, sentimientos y actitudes seleccionando:
                        * **F** = Falso
                        * **LV** = Ligeramente verdadero
                        * **BV** = Bastante verdadero
                        * **CV** = Completamente verdadero
                        """)
                        respuestas_pai = {}
                        with st.form("form_pai"):
                            for idx, preg in enumerate(ITEMS_PAI, 1):
                                respuestas_pai[f"p_{idx}"] = st.radio(
                                    preg, options=list(OPCIONES_PAI.keys()),
                                    format_func=lambda x: OPCIONES_PAI[x], horizontal=True, key=f"pai_{idx}"
                                )
                                st.divider()
                            if st.form_submit_button("Finalizar y Enviar PAI", use_container_width=True):
                                datos_token["evaluaciones"]["PAI"] = respuestas_pai
                                datos_token["estado"] = "finalizado"
                                guardar_token_db(token_actual, datos_token)
                                st.session_state["test_enviado"] = True
                                st.rerun()
