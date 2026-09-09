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
    
    # Obtener el hash del bloque anterior (Blockchain-lite para inalterabilidad)
    cursor.execute("SELECT hash_bloque FROM evaluaciones_periciales ORDER BY rowid DESC LIMIT 1")
    ultimo = cursor.fetchone()
    hash_prev = ultimo[0] if ultimo and ultimo[0] else "GENESIS_BLOCK_FORENSE"
    
    # Sello criptográfico encadenado
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
    """Extrae cabeceras HTTP de red para trazabilidad forense de IP y Dispositivo"""
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

# Cargamos el diccionario global desde SQLite en cada ejecución
claves_globales = cargar_datos_db()

if "perito_autenticado" not in st.session_state:
    st.session_state["perito_autenticado"] = False

def generar_token_unico(longitud=6):
    caracteres = string.ascii_uppercase + string.digits
    codigo = ''.join(random.choice(caracteres) for _ in range(longitud))
    return f"EVAL-{codigo}"

# -----------------------------------------------------------------------------
# 2. BANCO COMPLETO DE REACTIVOS DE LAS PRUEBAS (LSB-50 CORREGIDO SEGÚN PDF)
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
    "50. Tengo presentimientos de que va a pasar algo malo."
]
OPCIONES_LSB50 = {
    0: "0 - Nada", 
    1: "1 - Poco", 
    2: "2 - Moderadamente", 
    3: "3 - Bastante", 
    4: "4 - Mucho"
}

ITEMS_MMPI2RF = [
    "1. Me gustan las revistas de mecánica.",
    "2. Tengo buen apetito.",
    "3. Creo que me gustaría el trabajo de bibliotecario.",
    "4. Mi vida diaria está llena de cosas que mantienen mi interés.",
    "5. A veces he sentito un intenso deseo de abandonar mi hogar.",
    "6. Tengo dificultades para concentrarme en una tarea o trabajo.",
    "7. Mi madre es una buena mujer, (O si su madre ha fallecido) Mi madre era una buena mujer.",
    "8. Encuentro alivio cuando comparto mis problemas con alguien.",
    "9. A menudo me he sentido culpable porque he fingido mayor pesar del que realmente sentía.",
    "10. Cuesta mucho trabajo convencer a la mayoría de la gente de la verdad.",
    "11. Me gusta muchísimo ir a bailes.",
    "12. Frecuentemente siento que puedo leer la mente de otras personas.",
    "13. Algunas veces me empeño tanto en algo que las personas pierden la paciencia conmigo.",
    "14. En ocasiones los espíritus malignos se posesionan de mí.",
    "15. Siento un nudo en la garganta casi todo el tiempo.",
    "16. En ocasiones siento deseos de maldecir.",
    "17. Soy una persona muy sociable.",
    "18. Siento debilidad general la mayor parte del tiempo.",
    "19. Los miembros de mi familia y mis parientes más cercanos se llevan bastante bien.",
    "20. Me siento incómodo(a) cuando estoy en lugares cerrados.",
    "21. Cuando era más joven, a veces robé algunas cosas.",
    "22. Quisiera poder ser tan feliz como parecen serlo otras personas.",
    "23. A veces siento ganas de destrozar las cosas.",
    "24. Pierdo fácilmente las discusiones.",
    "25. Actualmente estoy tan capacitado(a) para trabajar como siempre lo he estado.",
    "26. Por principio, cuando alguien me hace algún mal siento que, de ser posible, debería pagarle con la misma moneda.",
    "27. Por lo general tengo las manos y los pies lo suficientemente calientes.",
    "28. Tiendo a tomar los desengaños tan a pecho que no puedo dejar de pensar en ellos.",
    "29. La mayor parte del tiempo me siento triste.",
    "30. No entiendo lo que leo tan bien como antes.",
    "31. He tenido experiencias muy peculiares y extrañas.",
    "32. Casi siempre tengo tos.",
    "33. Los fantasmas o los espíritus pueden influir en las personas para bien o para mal.",
    "34. Frecuentemente tengo que esforzarme para no demostrar que soy tímido(a).",
    "35. Creo que mucha gente exagera sus desgracias para que los demás se compadezcan de ellos y les ayuden.",
    "36. Las personas no lastiman mis sentimientos fácilmente.",
    "37. Nunca he tenido dificultades a causa de mi conducta sexual.",
    "38. Con frecuencia he tenido que recibir órdenes de personas que sabían menos que yo.",
    "39. Muchas veces he perdido oportunidades por no haberme decidido a tiempo.",
    "40. Casi siempre preferiría soñar despierto en lugar de hacer otra cosa.",
    "41. Algunas veces me gusta herir a las personas que quiero.",
    "42. Me gustaría ser soldado.",
    "43. Sufro ataques de náusea y de vómito.",
    "44. Me cuesta trabajo entablar una conversación con alguien que acabo de conocer.",
    "45. No siempre digo la verdad.",
    "46. Cuando estoy con gente me molesta oir cosas muy extrañas.",
    "47. Me gusta ir a fiestas y reuniones alegres y bulliciosas.",
    "48. Definitivamente no tengo confianza en mí mismo.",
    "49. He disfrutado fumando marihuana.",
    "50. Me gustaría ser cantante.",
    "51. He tenido miedo de cosas o personas que sabia que no podían hacerme daño.",
    "52. Muy raras veces padezco estreñimiento.",
    "53. A veces me siento lleno(a) de energia.",
    "54. Temo a los relámpagos.",
    "55. Creo que la mayoría de la gente mentiría para salir adelante.",
    "56. Me pongo nervioso(a) y preocupado(a) cuando tengo que salir de casa para hacer un viaje corto.",
    "57. Me gustan las reuniones sociales sólo por estar con la gente.",
    "58. Algunos de los mis familiares tienen hábitos que me molestan o irritan mucho.",
    "59. Mi memoria parece estar en buenas condiciones.",
    "60. Con frecuencia siento la necesidad de luchar por lo que creo justo.",
    "61. Nunca he hecho algo peligroso sólo por el gusto de hacerlo.",
    "62. Hago muchas cosas de las que luego me arrepiento. (Me arrepiento más o más frecuentemente que otras personas de las cosas que hago).",
    "63. Con frecuencia me ha parecido que algún extraño me miraba críticamente.",
    "64. Soy una persona importante.",
    "65. Casi nunca me ha dolido el corazón o el pecho.",
    "66. En la escuela algunas veces me llevaron ante el director por mala conducta.",
    "67. No me gusta tener gente a mi alrededor.",
    "68. Generalmente tengo que detenerme a pensar antes de hacer algo, aunque sea un asunto sin importancia.",
    "69. Mis manos no se han entorpecido ni perdido habilidad.",
    "70. No leo diariamente todos los artículos editoriales del periódico.",
    "71. Creo que están conspirando contra mí.",
    "72. A veces mis pensamientos han pasado por mi mente con tanta rapidez que no he podido expresarlos en palabras.",
    "73. No creo ser más nervioso(a) que la mayoría de las personas.",
    "74. Muchas veces tengo la sensación de haber hecho algo malo o diabólico.",
    "75. Creo que me gustaría trabajar como guardabosques.",
    "76. Padezco problemas estomacales varias veces a la semana.",
    "77. Soy tan susceptible respecto a algunos temas que ni siquiera puedo hablar de ellos.",
    "78. Aparentemente oigo tan bien como la mayoría de las personas.",
    "79. Tengo pesadillas varias veces a la semana.",
    "80. Tengo pocos disgustos con miembros de mi familia.",
    "81. A veces me dan ataques de risa o de llanto que no puedo controlar.",
    "82. No le tengo mucho miedo a las serpientes.",
    "83. Generalmente siento que la vida vale la pena.",
    "84. A veces siento deseos de empezar peleas a golpes.",
    "85. Nunca he tenido una visión.",
    "86. Solamente puedo expresar lo que en verdad siento, cuando tomo.",
    "87. La mayor parte de la gente es honrada principalmente por temor a ser descubierta.",
    "88. Muy raras veces siento dolor en la nuca.",
    "89. Definitivamente, a veces me siento un inútil.",
    "90. Temo encontrarme encerrado(a) en un ropero o en un lugar pequeño y cerrado.",
    "91. Me avergüenzo muy fácilmente.",
    "92. Creo que me están siguiendo.",
    "93. Recientemente he pensado en matarme.",
    "94. No me molesta conocer a personas extrañas.",
    "95. De vez en cuando dejo para mañana lo que debiera hacer hoy.",
    "96. A menudo mis padres se oponían a la clase de gente que frecuentaba.",
    "97. Me gusta conocer a gente importante porque eso me hace sentir importante.",
    "98. Quiero a mi padre. (O si su padre ha fallecido) Quise a mi padre.",
    "99. La mayor parte de la gente usaría medios injustos con tal de obtener lo que quiere.",
    "100. Me gusta la poesía.",
    "101. Muchas veces siento que me duele toda la cabeza.",
    "102. Me parece que soy tan listo(a) y capaz como la mayoria de los que me rodean.",
    "103. De vez en cuando siento odio hacia los miembros de mi familia a los que usualmente quiero.",
    "104. Generalmente defiendo con tenacidad mis propias opiniones.",
    "105. Casi siempre estoy feliz.",
    "106. He tenido épocas durante las cuales he hecho cosas que luego no recuerdo haber hecho.",
    "107. Me gusta hablar sobre temas sexuales.",
    "108. En varias ocasiones he dejado de hacer algo porque he dudado de mi habilidad.",
    "109. Disfruto con el alboroto de una multitud.",
    "110. Siento que frecuentemente he sido castigado(a) sin motivo.",
    "111. Creo que me gustaría el trabajo de contratista de obras.",
    "112. Tiendo a dejar de hacer algo que deseo cuando los demás piensan que esa no es la manera correcta de hacerlo.",
    "113. Casi nunca tengo calambres o dolores musculares.",
    "114. Desearía no ser tan tímido(a).",
    "115. No le temo al fuego.",
    "116. Tengo la tendencia a tomar las cosas muy en serio.",
    "117. Algo anda mal en mi mente.",
    "118. Me gusta coquetear.",
    "119. Pierdo fácilmente la paciencia con la gente.",
    "120. La mayor parte del tiempo desearía estar muerto(a).",
    "121. Es más seguro no confiar en nadie.",
    "122. He tenido ataques durante los cuales no podía controlar el habla o los movimientos, pero me daba cuenta de lo que ocurría a mí alrededor.",
    "123. Me preocupo mucho por posibles desgracias.",
    "124. Nunca he estado enamorado(a) de alguien.",
    "125. Mi manera de hablar es la misma de siempre (ni más rápida, ni más lenta, ni balbuceante, ni ronca).",
    "126. Me gustaba la escuela.",
    "127. Algunas veces me enojo.",
    "128. No tengo miedo de manejar dinero.",
    "129. Alguien ha intentado envenenarme.",
    "130. Me preocupo mucho.",
    "131. Cuando me aburro me gusta provocar algo emocionante o divertido.",
    "132. Con frecuencia cruzo la calle para evitar encontrarme con alguien que veo venir.",
    "133. Todo me sabe igual.",
    "134. No me enojo fácilmente.",
    "135. Me molesta mucho pensar en hacer cambios en mi vida.",
    "136. No me puedo concentrar en una sola cosa.",
    "137. Me parece tener la cabeza o la nariz congestionada la mayor parte del tiempo.",
    "138. Mis padres y familiares me encuentran más fallas de las que debieran.",
    "139. Frecuentemente oigo voces sin saber de dónde vienen.",
    "140. Disfruto de distintas clases de juegos y diversiones.",
    "141. He bebido alcohol con exceso.",
    "142. La mayoría de las personas hace amistades porque los amigos les pueden resultar útiles en algún momento.",
    "143. Algunas veces he sido un obstáculo para personas que querían hacer algo, no porque eso fuera importante, sino por cuestión de principios.",
    "144. Se me dificulta comenzar a hacer las cosas.",
    "145. Me gustaría ser florista.",
    "146. Casi todos los días sucede algo que me asusta.",
    "147. Me gusta hacerle saber a la gente mi punto de vista sobre las cosas.",
    "148. Me gusta mucho cazar.",
    "149. Algunas veces me vienen a la mente pensamientos sin importancia que me molestan por días.",
    "150. Alguien ha estado intentando robarme.",
    "151. Le tengo terror a los huracanes.",
    "152. Me rindo fácilmente cuando las cosas van mal.",
    "153. Mis preocupaciones parecen desaparecer cuando estoy con un grupo de amigos(as) animados(as).",
    "154. Mis modales en la mesa no son tan buenos en casa como cuando salgo a comer con otras personas.",
    "155. Me enojo con facilidad, pero se me pasa pronto.",
    "156. Recuerdo haberme fingido enfermo(a) para evitar algo.",
    "157. Cualquier persona que sea capaz y esté dispuesta a trabajar duro tiene buenas posibilidades de éxito.",
    "158. A menudo la vida me resulta difícil.",
    "159. He tenido momentos en los que mi mente se ha quedado en blanco y no me daba cuenta de lo que ocurría a mi alrededor.",
    "160. A veces creo que puedo tomar decisiones con extraordinaria facilidad.",
    "161. A menudo me vienen a la mente malas palabras, palabras horribles y me es imposible quitármelas de la cabeza.",
    "162. Nunca o casi nunca tengo mareos.",
    "163. Despierto descansado(a) y fresco(a) casi todas las mañanas.",
    "164. Últimamente he pensado mucho en matarme.",
    "165. Con frecuencia le tengo miedo a la oscuridad.",
    "166. Algunas veces sin razón, aun cuando me vaya mal, me siento muy alegre, como si estuviera en “la cima del mundo”.",
    "167. Me pone nervioso(a) tener que esperar.",
    "168. Hay personas que quieren apoderarse de mis pensamientos e ideas.",
    "169. El futuro me parece sin esperanzas.",
    "170. Puedo dormir durante el día pero no durante la noche.",
    "171. Creo que casi todo el mundo mentiría para evitar problemas.",
    "172. Con frecuencia, aun cuando todo vaya bien, siento que nada me importa.",
    "173. Cuando era niño(a) me golpearon muchas veces.",
    "174. Durante los últimos años he gozado de buena salud la mayor parte del tiempo.",
    "175. Nunca me siento más contento(a) que cuando estoy solo(a).",
    "176. A menudo siento como si tuviera una cinta que me apretara la cabeza.",
    "177. Por lo general no le hablo a la gente, hasta que ellos me hablan.",
    "178. Seria mejor que se desecharan casi todas las leyes.",
    "179. Algunas veces pierdo o me cambia la voz, aunque no esté resfriado(a).",
    "180. Algunos de mis familiares han hecho ciertas cosas que me han asustado.",
    "181. Una vez a la semana o más frecuentemente me pongo muy agitado(a).",
    "182. Tengo entera confianza en mi mismo.",
    "183. Prefiero ganar que perder en un juego.",
    "184. No le temo al agua.",
    "185. A la mayor parte de la gente le disgusta ayudar a los demás, aunque no lo diga.",
    "186. Nunca he tenido un ataque ni convulsiones.",
    "187. Algunas veces he sentido que las dificultades se acumulan de tal modo que no puedo vencerlas.",
    "188. Si fuera reportero(a) me gustaría mucho escribir notas deportivas.",
    "189. Muy pocas veces me duele la cabeza.",
    "190. Nunca he tenido problemas con la ley.",
    "191. Cuando camino tengo mucho cuidado de no pisar las rayas en las banquetas.",
    "192. Después de un mal día, generalmente necesito algunos tragos para relajarme.",
    "193. A veces me divierte tanto la astucia de algún criminal, que he deseado que se salga con la suya.",
    "194. Estoy seguro(a) de que la gente habla de mí.",
    "195. Cuando me siento triste, casi siempre algo emocionante me saca de ese estado.",
    "196. Me gusta el arte dramático.",
    "197. Generalmente le hablo claro a la gente a quien estoy tratando de mejorar o corregir.",
    "198. Me atemorizo ante las crisis o dificultades.",
    "199. A veces percibo olores raros.",
    "200. Es más difícil para mí concentrarme de lo que parece ser para otras personas.",
    "201. Me gustan las fiestas y las reuniones sociales.",
    "202. Nunca en mi vida me he sentido mejor que ahora.",
    "203. A veces mi alma abandona mi cuerpo.",
    "204. Aun cuando estoy acompañado(a) me siento solo(a) la mayor parte del tiempo.",
    "205. Cuando era chico(a) frecuentemente no iba a la escuela aunque debia haberlo hecho.",
    "206. Quisiera dejar de preocuparme por las cosas que he dicho y que quizás hayan herido los sentimientos de otras personas.",
    "207. Tengo periodos en que me siento muy alegre sin que exista una razón especial.",
    "208. Tengo miedo de usar cuchillos o cualquier otra cosa filosa o puntiaguda.",
    "209. Sin duda he tenido más cosas de qué preocuparme de las que me corresponderian.",
    "210. Sufro de malestares en la boca del estómago, varios días a la semana o más frecuentemente.",
    "211. No me agradan todas las personas que conozco.",
    "212. No tengo enemigos que realmente quieran hacerme daño.",
    "213. Las personas generalmente exigen más respeto para sus propios derechos, que el que están dispuestas a conceder a los demás.",
    "214. Aunque no estoy satisfecho(a) con mi vida, nada puedo hacer ahora para cambiarla.",
    "215. Con frecuencia tengo serios desacuerdos con personas importantes para mí.",
    "216. A veces me molesta oir tan bien.",
    "217. Muy rara vez me siento deprimido(a).",
    "218. A veces me ha sido imposible evitar robar o llevarme algo de una tienda.",
    "219. Algunas veces me siento tan-inquieto(a) que me es difícil quedarme dormido(a).",
    "220. No le temo a las arañas.",
    "221. Creo en el cumplimiento de la ley.",
    "222. Creo que hago amistades tan fácilmente como cualquiera.",
    "223. Cuando joven me suspendieron de la escuela una o más veces por mala conducta.",
    "224. Siempre tengo muy poco tiempo para terminar lo que hago.",
    "225. Me han dicho que camino cuando estoy dormido(a).",
    "226. Me gustaría ser corredor(a) de autos.",
    "227. No he tenido dificultad en mantener el equilibrio cuando camino.",
    "228. Casi todo el tiempo me siento preocupado(a) por algo o por alguien.",
    "229. Tiendo a dejar de hacer algo que quiero, si otros creen que eso no vale la pena.",
    "230. Tengo muchos problemas estomacales.",
    "231. Puedo atemorizar fácilmente a la gente y a veces lo hago para divertirme.",
    "232. A veces pienso que no sirvo para nada.",
    "233. La gente dice cosas ofensivas y vulgares acerca de mí.",
    "234. Actualmente no me siento estresado(a).",
    "235. Me molesta que la gente me mire en la calle, en las tiendas, etc.",
    "236. No me gusta escuchar a otras personas dar sus opiniones sobre la vida.",
    "237. Excepto por orden del médico, nunca he tomado drogas o pastillas para dormir.",
    "238. Cuando un hombre está con una mujer, casi siempre está pensando en cosas relacionadas con el sexo.",
    "239. Si me dieran la oportunidad sería un buen lider.",
    "240. Muchas veces siento como si las cosas no fueran reales.",
    "241. En ocasiones me gusta el chisme.",
    "242. A veces la parte superior de mi cabeza está muy sensible.",
    "243. La suciedad me molesta o me horroriza.",
    "244. Si me dieran la oportunidad, podria hacer algunas cosas que serían de gran beneficio para la humanidad.",
    "245. Si fuera periodista me gustaría mucho escribir sobre teatro.",
    "246. Por lo general espero tener éxito en lo que hago.",
    "247. Gran parte del tiempo me siento cansado(a).",
    "248. Me han dicho con frecuencia que tengo mal genio.",
    "249. En la escuela me era muy difícil hablar frente a la clase.",
    "250. Frecuentemente me siento apenado(a) por ser tan irritable y gruñón(a).",
    "251. Nadie lo sabe, pero he tratado de matarme.",
    "252. Alguien controla mi mente.",
    "253. En la escuela mis calificaciones en conducta generalmente eran malas.",
    "254. Raras veces noto los latidos de mi corazón, y muy pocas veces me falta la respiración.",
    "255. No me molesta mucho ver sufrir a los animales.",
    "256. Con frecuencia he conocido a personas supuestamente expertas y que no resultaron mejores que yo.",
    "257. Tengo pensamientos extraños y poco comunes.",
    "258. Me produce terror la idea de un terremoto.",
    "259. Me gusta reparar las cerraduras de las puertas.",
    "260. Frecuentemente he trabajado para personas que se atribuyen el reconocimiento por un buen trabajo pero culpan a los subalternos de los errores.",
    "261. Algunas veces me siento al borde de una crisis nerviosa.",
    "262. Estoy tan sano como la mayoría de mis amigos.",
    "263. Tengo que admitir que a veces me he preocupado más de la cuenta por cosas que no valían la pena.",
    "264. Alguien me tiene mala voluntad.",
    "265. Padezco poca o ninguna clase de dolores.",
    "266. Tengo problemas con el alcohol o las drogas.",
    "267. He tenido épocas en las que me sentia tan lleno de energía que en ocasiones, hasta por varios días, no necesitaba dormir.",
    "268. Nunca me preocupa mi apariencia fisica.",
    "269. Cuando las cosas van muy mal, sé que puedo contar con la ayuda de mi familia.",
    "270. Una o más veces en mi vida he sentido que alguien me obligaba a hacer cosas hipnotizándome.",
    "271. Me molesta que la gente me apresure.",
    "272. No tengo dificultades al tragar.",
    "273. Oigo cosas extrañas cuando estoy solo(a).",
    "274. En general tengo problemas para decidir qué debo hacer.",
    "275. Varias veces por semana siento como si algo terrible fuera a suceder.",
    "276. Cuando alguien hace algo que me enoja, le digo a la persona cómo me siento.",
    "277. Con frecuencia noto que mis manos tiemblan cuando trato de hacer algo.",
    "278. Siempre que me es posible evito estar entre mucha gente.",
    "279. La mayoria de los hombres son infieles a sus esposas de vez en cuando.",
    "280. Con frecuencia me confundo y se me olvida lo que quiero decir.",
    "281. Mi familia me trata más como un niño(a) que como un adulto.",
    "282. Los objetivos más importantes de mi vida están a mi alcance.",
    "283. Hablar con alguien sobre los problemas y preocupaciones es mucho mejor que tomar drogas o medicinas.",
    "284. Tengo miedo de estar solo(a) en un sitio al descubierto.",
    "285. A veces me parece que no puedo dejar de hablar.",
    "286. No le tengo miedo los ratones.",
    "287. Alguien ha tratado de influir en mi mente.",
    "288. Con frecuencia siento que no soy tan bueno(a) como otras personas.",
    "289. Con frecuencia he tenido miedo durante la noche.",
    "290. Casi nunca noto que me zumben o silben los oídos.",
    "291. Nunca me siento más feliz cuando estoy solo(a).",
    "292. Me gusta tener a los demás intrigados con respecto a lo que haré.",
    "293. Por lo general soy tranquilo(a) y no me altero fácilmente.",
    "294. A mí alrededor veo cosas, animales o personas que otros no ven.",
    "295. No temo entrar solo(a) a un salón donde hay gente reunida platicando.",
    "296. Me gustaría ser periodista.",
    "297. Me drogo o me emborracho por lo menos una vez a la semana.",
    "298. En las elecciones, algunas veces voto por candidatos que casi no conozco.",
    "299. Me siento incapaz cuando tengo que tomar una decisión importante.",
    "300. Me gusta mucho jugar deportes rudos (como fútbol americano o fútbol soccer).",
    "301. Se me adormecen una o varias partes de la piel.",
    "302. Me gusta tomar decisiones y asignar trabajo a otros.",
    "303. Con frecuencia me irrita mucho que me interrumpan cuando estoy trabajando.",
    "304. En la mayoría de los matrimonios uno o los dos miembros de la pareja son infelices.",
    "305. Me gustaría mucho ganarles a los criminales en sus fechorías.",
    "306. Olvido dónde dejo las cosas.",
    "307. Algunas veces he tenido pensamientos terribles acerca de mi familia.",
    "308. Con frecuencia me salen manchas rojas en el cuello.",
    "309. Me preocupa bastante el dinero.",
    "310. La gente no es muy amable conmigo.",
    "311. Algunas veces estoy seguro(a) que los demás pueden saber lo que estoy pensando.",
    "312. Cuando he estado tomado(a) me he enojado y he roto muebles y platos.",
    "313. Nunca he sufrido parálisis o alguna debilidad fuera de lo común en alguno de mis músculos.",
    "314. Odio a toda mi familia.",
    "315. Estoy tan harto(a) de lo que hago diariamente, que lo único que deseo es deshacerme de todo.",
    "316. A veces he tenido que ser rudo(a) con personas groseras o inoportunas.",
    "317. No puedo entrar solo(a) en un cuarto oscuro, aun en mi propia casa.",
    "318. En ocasiones me molesto y enojo tanto, que no sé que me pasa.",
    "319. A veces me es difícil defender mis derechos porque soy muy reservado(a).",
    "320. Ciertos animales me ponen nervioso(a).",
    "321. Me gusta negociar en situaciones difíciles.",
    "322. La crítica o el regaño me hieren profundamente.",
    "323. Cuando estoy triste, me ayuda a sentirse mejor visitar a los amigos.",
    "324. Me pongo nervioso(a) cuando tengo que tomar decisiones importantes.",
    "325. A veces me río de los chistes obscenos.",
    "326. La mayoría des las parejas casadas no se demuestran mucho afecto.",
    "327. Con frecuencia me esfuerzo para superar a alguien que me ha llevado la contraria.",
    "328. Si me enojo, sé con seguridad que me dará dolor de cabeza.",
    "329. Me he llegado a sentir tan enojado(a) que he lastimado a otra persona en un pleito a puñetazos.",
    "330. En ocasiones me parece escuchar lo que pienso en voz alta.",
    "331. Cuando la vida se pone difícil, quisiera tan sólo rendirme.",
    "332. Si la gente no hubiera querido perjudicarme, hubiera tenido más éxito en la vida.",
    "333. No me canso con facilidad.",
    "334. Últimamente, mis pensamientos están más y más relacionados con la muerte y con la vida después de la muerte.",
    "335. Me enojo conmigo mismo(a) cuando accedo demasiado a los deseos de los demás.",
    "336. Reconozco que tengo varios defectos que no seré capaz de cambiar.",
    "337. Me he enojado tanto con alguien, que he sentido como si fuera a explotar.",
    "338. Frecuentemente me encuentro preocupado(a) por algo."
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

# Banco completo de los 344 reactivos oficiales del PAI
ITEMS_PAI = [
    "1. Me preocupa mi salud más que a la mayoría de la gente.", "2. A veces me siento tan deprimido que nada puede animarme.",
    "3. Tengo pensamientos que prefiero no compartir con nadie.", "4. Me resulta difícil concentrarse en una tarea.",
    "5. Mis planes rara vez salen como los imagino.", "6. Me molesta profundamente que la gente me interrumpa.",
    "7. He tenido experiencias muy extrañas que otros no comprenden.", "8. Me siento seguro de mí mismo la mayor parte del tiempo.",
    "9. A veces consumo alcohol o sustancias para calmar mis nervios.", "10. Siento que las personas de mi entorno conspiran contra mí.",
    "11. Me cuesta conciliar el sueño por las noches.", "12. Tengo dolores frecuentes en la cabeza o en el cuello.",
    "13. A veces siento que pierdo el control de mis actos.", "14. Me considero una persona muy perfeccionista.",
    "15. Mis cambios de humor son frecuentes y bruscos.", "16. Me cuesta confiar en las intenciones de los demás.",
    "17. Siento que la vida no tiene sentido para mí.", "18. A veces escucho ruidos o susurros que otros no oyen.",
    "19. Me pongo muy tenso en situaciones sociales.", "20. Tengo problemas digestivos cuando estoy nervioso.",
    "21. Siento una necesidad irresistible de comprobar las cosas varias veces.", "22. Me agrada correr riesgos innecesarios.",
    "23. A veces creo que tengo poderes o capacidades especiales.", "24. Me siento culpable por cosas que hice en el pasado.",
    "25. Me resulta fácil hablar en público sin ponerme nervioso.", "26. Tengo explosiones de ira que no puedo controlar.",
    "27. Me preocupa contraer una enfermedad grave.", "28. Siento que nadie me comprende verdaderamente.",
    "29. A veces experimento una felicidad o energía desmedida.", "30. Me disgusta profundamente seguir reglas estrictas.",
    "31. Siento opresión en el pecho con frecuencia.", "32. Me cuesta tomar decisiones cotidianas.",
    "33. A veces dudo de si lo que veo o siento es real.", "34. Sigo reviviendo algo horrible que me ocurrió en el pasado.",
    "35. Me considero superior a la mayoría de las personas.", "36. A menudo me siento fatigado sin motivo aparente.",
    "37. Me molesta enormemente que me den órdenes.", "38. Siento que la gente habla a mis espaldas.",
    "39. Tengo pensamientos recurrentes de hacerme daño.", "40. Me resulta sencillo hacer amigos nuevos.",
    "41. Me aterra estar en espacios cerrados o pequeños.", "42. A veces actúo de forma imprudente sin pensar en las consecuencias.",
    "43. Siento una profunda tristeza que no se disipa.", "44. Me molesta el desorden o la falta de simetría.",
    "45. Creo que hay un complot en mi contra.", "46. Me cuesta mantener la atención en una lectura prolongada.",
    "47. A veces siento descargas o entumecimiento en las manos.", "48. Me considero una persona rencorosa.",
    "49. Disfruto desafiando a la autoridad.", "50. Siento que mi memoria está fallando.",
    "51. Tengo miedo de perder la razón.", "52. Me irrita que la gente sea impuntual.",
    "53. Siento que mis logros no son valorados.", "54. A veces tengo dificultades para respirar con normalidad.",
    "55. Tengo algunas dificultades para controlar la cantidad de alcohol que bebo.", "56. Me siento culpable por descansar o no hacer nada.",
    "57. A veces veo sombras o figuras que desaparecen rápido.", "58. Me cuesta aceptar las críticas constructivas.",
    "59. Siento que el futuro es totalmente desesperanzador.", "60. Me gusta llamar la atención en las reuniones.",
    "61. Tengo palpitaciones repentinas sin haber hecho esfuerzo físico.", "62. Me agobia la presión del trabajo o los estudios.",
    "63. A veces siento que mi cuerpo no me pertenece.", "64. Me cuesta perdonar las ofensas graves.",
    "65. Creo que las leyes están hechas para romperse.", "66. Siento una intensa ansiedad sin causa aparente.",
    "67. Me preocupa excesivamente cometer errores.", "68. A veces pierdo la noción del tiempo por completo.",
    "69. Me siento solo incluso estando rodeado de gente.", "70. Disfruto compitiendo y ganando a los demás.",
    "71. Tengo fobias o miedos específicos difíciles de explicar.", "72. A veces consumo pastillas o medicamentos para dormir.",
    "73. Siento que alguien intenta interferir en mis pensamientos.", "74. Me cuesta expresar afecto o ternura.",
    "75. Tengo ataques de llanto incontrolable.", "76. Me molesta profundamente que me contradigan.",
    "77. Siento dolores musculares persistentes en la espalda.", "78. A veces me invade una rabia destructiva.",
    "79. Me considero una persona sumamente cautelosa.", "80. A veces recibo por correo anuncios que no me interesan en absoluto.",
    "81. Siento que la suerte jamás me acompaña.", "82. Me cuesta trabajo delegar responsabilidades.",
    "83. A veces siento destellos de luz extraños en los ojos.", "84. Me disgusta la compañía de personas pesimistas.",
    "85. Siento que mi vida carece de metas claras.", "86. Me exijo demasiado a mí mismo.",
    "87. A veces tengo pesadillas recurrentes y muy desagradables.", "88. Me resulta fácil manipular a los demás para conseguir lo que quiero.",
    "89. Siento mareos repentinos al ponerme de pie.", "90. Me aterra el fracaso en mis proyectos.",
    "91. A veces siento que los objetos a mi alrededor cambian de tamaño.", "92. Me irrita la incompetencia ajena.",
    "93. Siento un vacío profundo en mi interior.", "94. Me gusta experimentar emociones fuertes y peligrosas.",
    "95. Creo que las personas son egoístas y malintencionadas.", "96. Me cuesta concentrarme cuando hay ruido.",
    "97. A veces noto temblores involuntarios en las manos.", "98. Me cuesta adaptarme a los cambios imprevistos.",
    "99. Siento que merezco un castigo por mis faltas.", "100. He hecho planes para matarme.",
    "101. Me preocupa contraer gérmenes o contagiarme de suciedad.", "102. A veces actúo impulsivamente y luego me arrepiento.",
    "103. Siento que mi mente está completamente bloqueada.", "104. Me molesta que las cosas no se hagan a mi manera.",
    "105. A veces dudo de mi propia identidad o género.", "106. Me cuesta mantener relaciones estables.",
    "107. Siento una tensión constante en la mandíbula.", "108. Me agrada criticar las costumbres de otros.",
    "109. A veces experimento sensaciones de flotar fuera de mi cuerpo.", "110. Me siento incapaz de superar mis problemas.",
    "111. Tengo miedo de quedarme solo en casa por la noche.", "112. A veces consumo drogas para sentirme mejor.",
    "113. Siento que mis pensamientos son escuchados por otros.", "114. Me cuesta mostrar empatía con el sufrimiento ajeno.",
    "115. Tengo altibajos emocionales muy marcados durante el día.", "116. Me molesta profundamente la lentitud de los demás.",
    "117. Siento ardor estomacal constante por los nervios.", "118. A veces me imagino haciendo daño a alguien.",
    "119. Me considero una persona prudente y ahorrativa.", "120. A veces me pregunto si la gente dice la verdad.",
    "121. Siento que nadie valora mi esfuerzo laboral.", "122. Me cuesta relajarme incluso en vacaciones.",
    "123. A veces escucho voces que comentan lo que hago.", "124. Me desagrada participar en eventos sociales masivos.",
    "125. Siento que la desesperación se apodera de mí.", "126. Me gusta liderar y dirigir grupos de personas.",
    "127. Tengo molestias físicas sin causa médica aparente.", "128. A veces rompo objetos cuando me enfurezco.",
    "129. Me preocupa excesivamente el orden y la simetría.", "130. A veces siento que el tiempo pasa muy lento.",
    "131. Siento que los demás se aprovechan de mi bondad.", "132. Me cuesta trabajo decir que no a las peticiones.",
    "133. A veces veo manchas o destellos luminosos extraños.", "134. Me irrita la gente que muestra debilidad.",
    "135. Siento que mi vida es un fracaso absoluto.", "136. Me atraen los juegos de azar y las apuestas.",
    "137. Tengo dolores punzantes en el pecho ocasionalmente.", "138. A veces me siento invulnerable y capaz de todo.",
    "139. Me preocupa contraer una enfermedad incurable.", "140. Me cuesta mantener un horario constante.",
    "141. A veces siento que mis extremidades no me obedecen.", "142. Me disgusta la gente deshonesta.",
    "143. Siento una tristeza profunda al despertar.", "144. Me gusta impresionar a los demás con mis logros.",
    "145. Creo que hay fuerzas ocultas que me manipulan.", "146. Me cuesta concentrarse si hay distracciones visuales.",
    "147. Tengo problemas frecuentes de sudoración en las manos.", "148. Me agrada llevar la contraria en las discusiones.",
    "149. Siento que la culpa no me deja en paz.", "150. Me aterra hablar en público.",
    "151. Tengo fobias a ciertos animales o insectos.", "152. A veces tomo medicamentos sin prescripción médica.",
    "153. Siento que mis ideas son plagiadas por otros.", "154. Me cuesta perdonar los errores ajenos.",
    "155. Tengo cambios de humor repentinos sin motivo.", "156. Me molesta que me interrumpan cuando hablo.",
    "157. Siento molestias en las articulaciones al estresarme.", "158. A veces pierdo el autocontrol verbalmente.",
    "159. Me considero una persona sumamente organizada.", "160. A veces dudo de las intenciones de mis amigos.",
    "161. Siento que el mundo es un lugar hostil.", "162. Me cuesta delegar tareas en el trabajo.",
    "163. A veces siento zumbidos extraños en los oídos.", "164. Me desagrada la gente demasiado efusiva.",
    "165. Siento que ya no tengo esperanzas de mejorar.", "166. Me exijo la perfección en todo lo que hago.",
    "167. Tengo recuerdos angustiosos del pasado que vuelven.", "168. Me resulta fácil engatusar a la gente.",
    "169. Siento debilidad general en las piernas.", "170. Me aterra cometer un error grave.",
    "171. A veces siento que el espacio a mi alrededor se distorsiona.", "172. Me irrita la falta de limpieza.",
    "173. Siento un vacío emocional permanente.", "174. Me gusta correr riesgos físicos.",
    "175. Creo que las instituciones protegen a los corruptos.", "176. Me cuesta mantener la atención prolongada.",
    "177. Tengo espasmos musculares cuando estoy ansioso.", "178. Me cuesta aceptar las normas sociales impuestas.",
    "179. Siento que merezco sufrir por mis errores.", "180. He pensado en formas de desaparecer.",
    "181. Me preocupa la limpieza excesiva de las manos.", "182. A veces actúo sin medir las consecuencias.",
    "183. Siento que mi mente está nublada y confusa.", "184. Me molesta que no sigan mis instrucciones.",
    "185. A veces dudo de si existo realmente.", "186. Me cuesta comprometerme afectivamente.",
    "187. Siento rigidez en los hombros y cuello.", "188. Me agrada criticar los errores de los demás.",
    "189. A veces experimento la sensación de estar muerto en vida.", "190. Siento que nadie me aprecia.",
    "191. Tengo pánico a las alturas o puentes.", "192. A veces consumo alcohol para olvidar mis problemas.",
    "193. Siento que mis pensamientos son transmitidos en alta voz.", "194. Me cuesta demostrar compasión.",
    "195. Tengo altibajos de energía muy intensos.", "196. Me molesta la lentitud en los trámites.",
    "197. Siento opresión estomacal ante los problemas.", "198. A veces tengo impulsos de romper cosas.",
    "199. Me considero una persona sumamente cautelosa y formal.", "200. A veces dudo de la fidelidad de mi pareja.",
    "201. Siento que mi trabajo no es reconocido.", "202. Me cuesta desconectarme de las preocupaciones.",
    "203. A veces escucho voces que me insultan.", "204. Me disgusta relacionarme con gente desconocida.",
    "205. Siento una desesperación abrumadora.", "206. No me interesa la vida.",
    "207. Tengo molestias físicas recurrentes sin causa orgánica.", "208. A veces agredo verbalmente a quienes me molestan.",
    "209. Me preocupa que las cosas no estén perfectamente alineadas.", "210. A veces siento que el tiempo pasa demasiado rápido.",
    "211. Siento que la gente conspira contra mi éxito.", "212. Me cuesta decir que no ante la presión.",
    "213. A veces veo destellos extraños en la oscuridad.", "214. Me irrita la gente ignorante.",
    "215. Siento que mi vida es un completo fracaso.", "216. Me atraen las emociones prohibidas.",
    "217. Tengo dolores de cabeza tensionales frecuentes.", "218. A veces me siento con una fuerza sobrehumana.",
    "219. Me preocupa contraer una enfermedad contagiosa grave.", "220. Me cuesta mantener una rutina diaria.",
    "221. A veces siento adormecimiento en la cara.", "222. Me disgusta la gente falsa.",
    "223. Siento una profunda melancolía al caer la tarde.", "224. Me gusta ser el centro de atención.",
    "225. Creo que hay personas que me vigilan.", "226. Me cuesta concentrarme si hay luz brillante.",
    "227. Tengo problemas de transpiración excesiva.", "228. Me agrada provocar discusiones.",
    "229. Siento que la culpa me atormenta día y noche.", "230. Me aterra hablar con personas desconocidas.",
    "231. Tengo fobias a los espacios abiertos (agorafobia).", "232. A veces tomo sustancias para escapar de la realidad.",
    "233. Siento que mis ideas son robadas por otros.", "234. Sigo teniendo pesadillas sobre el pasado.",
    "235. Tengo cambios de humor impredecibles.", "236. Me molesta que cambien mis planes.",
    "237. Siento molestias intestinales por estrés.", "238. A veces pierdo el control y grito a los demás.",
    "239. Me considero una persona meticulosa.", "240. A veces dudo de la lealtad de mis amigos.",
    "241. Siento que nadie apoya mis iniciativas.", "242. Me cuesta dormir por pensar en el día siguiente.",
    "243. A veces escucho murmullos confusos.", "244. Me desagrada el trato con el público.",
    "245. Siento una angustia que me paraliza.", "246. Me gusta mandar y organizar a los demás.",
    "247. Tengo dolores corporales vagos y cambiantes.", "248. A veces tengo deseos violentos de golpear algo.",
    "249. A veces veo sólo en blanco y negro.", "250. A veces siento que el mundo es irreal.",
    "251. Siento que los demás me envidian.", "252. Me cuesta rechazar favores.",
    "253. A veces veo siluetas extrañas.", "254. Me irrita la gente desorganizada.",
    "255. Siento que no valgo nada como persona.", "256. Me atrae la velocidad y el peligro.",
    "257. Tengo cefaleas crónicas.", "258. A veces me siento eufórico y sin descanso.",
    "259. Me preocupa enfermarme gravemente.", "260. Me cuesta cumplir con los plazos.",
    "261. A veces siento pinchazos en las extremidades.", "262. Me disgusta la injusticia.",
    "263. Siento una tristeza infinita.", "264. Me gusta alardear de mis capacidades.",
    "265. Creo que intentan perjudicarme.", "266. Me cuesta leer textos largos.",
    "267. Tengo mareos al levantarme rápido.", "268. Me agrada desafiar las normas.",
    "269. Siento que el remordimiento me consume.", "270. Me aterra el rechazo social.",
    "271. Tengo pánico a las tormentas o animales.", "272. A veces consumo alcohol en exceso.",
    "273. Siento que leen mi mente.", "274. Tuve una experiencia muy mala que me ha hecho perder el interés por algunas cosas con las que antes disfrutaba.",
    "275. Tengo altibajos emocionales intensos.", "276. Me molesta que me den consejos.",
    "277. Siento tensión en el cuello.", "278. A veces pierdo los estribos.",
    "279. Me considero muy ordenado.", "280. A veces desconfío de todos.",
    "281. Siento que mi esfuerzo no cuenta.", "282. Me cuesta apagar la mente para dormir.",
    "283. A veces oigo voces extrañas.", "284. Me disgusta la muchedumbre.",
    "285. Siento una desesperanza total.", "286. Me gusta dirigir todo.",
    "287. Tengo dolores musculares frecuentes.", "288. A veces rompo cosas de la rabia.",
    "289. Me preocupa el orden extremo.", "290. A veces el tiempo se detiene.",
    "291. Siento que conspiran contra mí.", "292. Me cuesta poner límites.",
    "293. A veces veo cosas raras.", "294. Me irrita la torpeza.",
    "295. Siento que mi vida es un desastre.", "296. Me atraen las deudas y riesgos.",
    "297. Tengo migrañas frecuentes.", "298. A veces tengo energía inagotable.",
    "299. Me preocupa la salud constantemente.", "300. Me cuesta seguir horarios.",
    "301. Siento calambres por ansiedad.", "302. Me disgusta la trampa.",
    "303. Siento una profunda pena.", "304. Me gusta presumir.",
    "305. Creo que me persiguen.", "306. Me cuesta concentrarme.",
    "307. Tengo fatiga crónica.", "308. Me agrada romper reglas.",
    "309. Soy objeto de una conspiración.", "310. Me aterra fallar.",
    "311. Tengo fobias intensas.", "312. A veces bebo para calmarme.",
    "313. Siento que controlan mis actos.", "314. Me cuesta perdonar.",
    "315. Tengo altibajos de humor.", "316. Me molesta la prisa.",
    "317. Siento opresión corporal.", "318. A veces exploto de ira.",
    "319. Me considero perfectionista.", "320. A veces desconfío de mis amigos.",
    "321. Siento que nadie me apoya.", "322. Me cuesta descansar.",
    "323. A veces oigo susurros.", "324. Me disgusta socializar.",
    "325. Siento una angustia infinita.", "326. Me gusta mandar.",
    "327. Tengo dolores vagos.", "328. A veces tengo impulsos agresivos.",
    "329. Me preocupa la simetría.", "330. A veces el tiempo vuela.",
    "331. Siento que me envidian.", "332. Me cuesta negarme.",
    "333. A veces veo sombras.", "334. Me irrita la incompetencia.",
    "335. Siento que no sirvo para nada.", "336. Me atrae el peligro.",
    "337. Tengo dolores tensionales.", "338. A veces tengo una vitalidad desmedida.",
    "339. Me preocupa enfermar.", "340. Estoy pensando en la posibilidad de suicidarme.",
    "341. Siento temblores frecuentes.", "342. Me disgusta la mentira.",
    "343. Siento una profunda tristeza interna.", "344. Me gusta destacar en todo."
]

OPCIONES_PAI = {
    0: "0 - Falsa, nada en absoluto",
    1: "1 - Ligeramente verdadera, algo",
    2: "2 - Bastante verdadera, moderadamente",
    3: "3 - Completamente verdadera, mucho"
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
                    
                    # Metadatos de Red y Bloque Inalterable
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
            # Control Antispoofing / Aviso de cambio de IP
            ip_registrada = datos_token.get("ip_acceso")
            if ip_registrada and ip_registrada != "IP_LOCAL_O_NO_DETECTADA" and ip_registrada != ip_cliente:
                st.warning("⚠️ **Aviso de seguridad forense:** Se detecta variación en la red de conexión respecto a la emisión inicial del token. Esta incidencia queda registrada para control de cadena de custodia.")

            # PASO 2: Cargar Datos Personales
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
                            # Fijar metadatos de red y dispositivo al token
                            datos_token["ip_acceso"] = ip_cliente
                            datos_token["user_agent"] = ua_cliente
                            
                            guardar_token_db(token_actual, datos_token)
                            st.rerun()
                        else:
                            st.warning("Por favor complete sus Nombre, Apellido y DNI para poder avanzar.")
            
            # PASO 3: Selección de Cuestionarios y Escalas
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
                        * **0** = Nada | **1** = Poco | **2** = Moderadamente | **3** = Bastante | **4** = Mucho
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
                        **Instrucciones:** Para cada afirmación, indique cuál de las siguientes opciones describe mejor su situación:
                        * **0** = Falsa, nada en absoluto | **1** = Ligeramente verdadera, algo | **2** = Bastante verdadera, moderadamente | **3** = Completamente verdadera, mucho
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
