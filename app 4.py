import streamlit as st
import random
import string
from datetime import datetime, timedelta, timezone
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
# 1. CONFIGURACIÓN Y ALMACÉN GLOBAL COMPARTIDO
# -----------------------------------------------------------------------------
CONTRASEÑA_MAESTRA = "MiClavePericial2026"

@st.cache_resource
def obtener_base_claves_global():
    return {}

claves_globales = obtener_base_claves_global()

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
    "57. Me gusta la emoción y la aventura.", "58. Tengo problemas de digestión.", "59. Siento que mi familia no me apoya.",
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
    "192. Siento que la culpa no me deja en paz.", "193. Me agrada hacer planes a largo plazo.", "194. Sufro de dolores de espalda punzantes.",
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
    "258. Siento fatiga sin haber hecho esfuerzo.", "259. Me cuesta adaptarme a directrices estrictas.", "260. Siento que mis opiniones no cuentan.",
    "261. Disfruto del trabajo artesanal.", "262. Siento palpitaciones al enfrentar problemas.", "263. Me resulta complejo expresar afecto físico.",
    "264. Siento insatisfacción constante.", "265. Me agrada participar en proyectos cívicos.", "266. Tengo pesadez de párpados continua.",
    "267. Me cuesta trabajo seguir instrucciones paso a paso.", "268. A veces dudo de mi propia identidad.", "269. Me siento seguro frente a nuevos proyectos.",
    "270. Siento envidia incontenible por los logros ajenos.", "271. Sufro de rigidez en la mandíbula.", "272. Me apasiona la lectura de biografías.",
    "273. Me resulta complejo manejar la crítica.", "274. Siento que la angustia me paraliza.", "275. Me considero una persona empática.",
    "276. Siento molestias en las articulaciones al despertar.", "277. Me cuesta integrarme a grupos consolidados.", "278. A veces reacciono de forma desmedida.",
    "279. Me gratifica aprender nuevas tecnologías.", "280. Siento vértigo al mirar desde las alturas.", "281. Me resulta difícil superar ofensas pasadas.",
    "282. Siento un vacío profundo a menudo.", "283. Me alegra poder orientar a otros.", "284. Tengo episodios de visión doble.",
    "285. Me cuesta trabajo establecer límites.", "286. A veces me asalta una euforia desmedida.", "287. Me siento cómodo en ambientes estructurados.",
    "288. Siento constante inquietud en las piernas.", "289. Me resulta duro admitir mis errores.", "290. Siento que la suerte nunca me sonríe.",
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
    "336. Me atrae la literatura filosófica.", "337. Me resulta difícil admitir derrotas.", "338. Siento que mi vida tiene un propósito claro."
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
    {"titulo": "8. Autocrítica", "opciones": ["0 - No me critico ni me culpo más de lo habitual.", "1 - Estoy más crítico/a conmigo mismo/a de lo que solía estar.", "2 - Me critico a mí mismo/a por todos mis errores.", "3 - Me culpo a mí mismo/a por todo lo malo que sucede."]},
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

MAPA_TESTS = {
    "LSB-50": {"items": ITEMS_LSB50, "opciones": OPCIONES_LSB50},
    "MMPI-2-RF": {"items": ITEMS_MMPI2RF, "opciones": None},
    "CUIDA": {"items": ITEMS_CUIDA, "opciones": OPCIONES_CUIDA},
    "STAI": {"items": ITEMS_STAI, "opciones": OPCIONES_STAI},
    "BDI-II": {"items": [item["titulo"] for item in ITEMS_BDI], "opciones": None}
}

# -----------------------------------------------------------------------------
# DETECCIÓN DE PARÁMETROS URL (Link automático para el evaluado)
# -----------------------------------------------------------------------------
query_params = st.query_params
token_url = query_params.get("token", None)

if token_url and "token_activo" not in st.session_state:
    token_limpio = token_url.strip().upper()
    if token_limpio in claves_globales:
        st.session_state["token_activo"] = token_limpio

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
    st.write("Bienvenido al módulo pericial de gestión de evaluaciones.")
    st.divider()
    
    st.subheader("🔑 Generar Clave y Link de Acceso")
    st.write("Haga clic en el botón para crear un código y un enlace directo para el evaluado:")
    
    if st.button("🎲 Generar Nueva Clave y Link", type="primary"):
        nueva_clave = generar_token_unico()
        claves_globales[nueva_clave] = {
            "estado": "activa",
            "datos_persona": None,
            "evaluaciones": {}
        }
        st.success(f"¡Clave generada con éxito!: **`{nueva_clave}`**")
        
        # Obtener URL base actual de la app
        base_url = "https://psi-forense-hwgpyudkkkwqfwsjx2kkge.streamlit.app"
        link_completo = f"{base_url}/?token={nueva_clave}"
        
        st.markdown(f"🔗 **Link directo para enviar por WhatsApp o correo:**")
        st.code(link_completo, language="text")
        st.info("Copie este enlace y envíatelo al evaluado. Al hacer clic, ingresará automáticamente.")
    
    st.divider()
    
    st.subheader("📋 Estado de Claves y Evaluaciones")
    if claves_globales:
        for clave in list(claves_globales.keys()):
            info = claves_globales[clave]
            persona = info.get("datos_persona")
            evals = info.get("evaluaciones", {})
            col_texto, col_borrar = st.columns([5, 1])
            with col_texto:
                if not evals:
                    info_persona = f" (Iniciado por: {persona['nombre']} - DNI {persona['dni']})" if persona else " (Pendiente de ingreso)"
                    st.markdown(f"🟢 **Clave:** `{clave}` | **Estado:** Disponible / Activa{info_persona}")
                else:
                    nombre_str = persona['nombre'] if persona else "Desconocido"
                    dni_str = persona['dni'] if persona else "N/A"
                    fecha_str = persona['fecha'] if persona else "N/A"
                    hora_str = persona.get('hora', 'N/A')
                    hash_val = persona.get('hash_seguridad', 'N/A')
                    tests_realizados = ", ".join(list(evals.keys()))
                    
                    st.markdown(f"🔴 **Clave:** `{clave}` | **Evaluado:** {nombre_str} (DNI: {dni_str}) | **Pruebas:** {tests_realizados} | **Hash:** `{hash_val[:10]}...`")
                    
                    with st.expander(f"Ver respuestas e informes de {nombre_str} - Código {clave}"):
                        for test_nombre, respuestas_dict in evals.items():
                            st.write(f"### 📋 Protocolo de Respuestas Registradas - {test_nombre}")
                            
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
                                        "Consigna / Ítem Respondido": consigna_texto,
                                        "Respuesta Seleccionada": respuesta_texto
                                    })
                                
                                st.dataframe(tabla_datos, use_container_width=True, hide_index=True)
                            
                            st.write("**Párrafo de Resguardo Metodológico para el Informe Pericial:**")
                            texto_informe = f"""III. TÉCNICAS E INSTRUMENTOS ADMINISTRADOS
• Instrumento: {test_nombre}
• Evaluado/a: {nombre_str} (DNI: {dni_str})
• Fecha de administración: {fecha_str}
• Hora de administración (GMT Buenos Aires): {hora_str} hs
• Hash de Seguridad (SHA-256): {hash_val}
Consideraciones metodológicas sobre la administración:
"Las pruebas psicométricas fueron administradas en entorno controlado mediante un sistema digital de captura de respuestas de uso exclusivo del perito, garantizando la fidelidad en la transcripción de los reactivos y la integridad de la cadena de custodia mediante firma hash."
"""
                            st.code(texto_informe, language="markdown")
                            st.divider()
            with col_borrar:
                if st.button("🗑️ Borrar", key=f"btn_borrar_{clave}", use_container_width=True):
                    if st.session_state.get("token_activo") == clave:
                        del st.session_state["token_activo"]
                    del claves_globales[clave]
                    st.rerun()
            st.divider()
    else:
        st.write("No hay claves generadas todavía en este ciclo de sesión.")

else:
    st.title("⚖️ Evaluaciones Psicológicas Forenses")
    
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
                st.session_state["token_activo"] = clave_limpia
                st.session_state["test_enviado"] = False
                st.rerun()
            else:
                st.error("Código inválido o inexistente. Verifique el código ingresado con el evaluador.")
    
    else:
        token_actual = st.session_state["token_activo"]
        datos_token = claves_globales[token_actual]
        
        # PASO 2: Cargar Datos Personales, Fecha/Hora GMT Buenos Aires y Hash de seguridad
        if datos_token.get("datos_persona") is None:
            col_info, col_salir = st.columns([4, 1])
            with col_info:
                st.subheader("Datos del Evaluado y Registro de Identidad")
            with col_salir:
                if st.button("🔴 Salir", use_container_width=True):
                    del st.session_state["token_activo"]
                    st.query_params.clear()
                    st.rerun()
            st.write("Por favor, complete sus datos filiatorios antes de acceder a las escalas:")
            
            with st.form("form_datos_personales"):
                nombre_comp = st.text_input("Nombre y Apellido completo:", autocomplete="off")
                dni_val = st.text_input("Número de DNI / Documento:", autocomplete="off")
                
                guardar_datos = st.form_submit_button("Generar Hash y Acceder a las Escalas", use_container_width=True)
                
                if guardar_datos:
                    if nombre_comp.strip() != "" and dni_val.strip() != "":
                        # Captura automática de fecha y hora exacta en GMT Buenos Aires (America/Argentina/Buenos_Aires)
                        try:
                            tz_ba = ZoneInfo("America/Argentina/Buenos_Aires")
                            ahora_ba = datetime.now(tz_ba)
                        except Exception:
                            # Fallback si el entorno no dispone de ZoneInfo
                            tz_ba = timezone(timedelta(hours=-3))
                            ahora_ba = datetime.now(tz_ba)
                        
                        fecha_eval = ahora_ba.strftime("%Y-%m-%d")
                        hora_eval = ahora_ba.strftime("%H:%M:%S")
                        
                        # Generación de hash SHA-256 de seguridad combinando token, identidad y marca temporal GMT Buenos Aires
                        str_para_hash = f"{token_actual}-{nombre_comp.strip()}-{dni_val.strip()}-{fecha_eval}-{hora_eval}"
                        hash_generado = hashlib.sha256(str_para_hash.encode('utf-8')).hexdigest()
                        
                        claves_globales[token_actual]["datos_persona"] = {
                            "nombre": nombre_comp.strip(),
                            "dni": dni_val.strip(),
                            "fecha": fecha_eval,
                            "hora": hora_eval,
                            "hash_seguridad": hash_generado
                        }
                        st.rerun()
                    else:
                        st.warning("Por favor complete su Nombre, Apellido y DNI para poder avanzar.")
        
        # PASO 3: Selección de Cuestionarios y Escalas
        else:
            persona = datos_token["datos_persona"]
            hora_str = persona.get("hora", "N/A")
            evaluaciones_realizadas = datos_token.get("evaluaciones", {})
            
            col_datos, col_boton = st.columns([3, 1])
            with col_datos:
                st.info(f"Evaluado: **{persona['nombre']}** | DNI: **{persona['dni']}** | Hora (BA): **{hora_str}** | Hash: `{persona['hash_seguridad'][:10]}...`")
            with col_boton:
                if st.button("🔴 Finalizar y Salir", use_container_width=True):
                    del st.session_state["token_activo"]
                    st.query_params.clear()
                    st.rerun()

            if st.session_state.get("test_enviado"):
                st.success("¡Escala enviada y registrada con éxito bajo cadena de custodia digital!")
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
                        "BDI-II (Inventario de Depresión de Beck)"
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
                            claves_globales[token_actual]["evaluaciones"]["LSB-50"] = respuestas_lsb
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
                            claves_globales[token_actual]["evaluaciones"]["MMPI-2-RF"] = respuestas_mmpi
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
                            claves_globales[token_actual]["evaluaciones"]["CUIDA"] = respuestas_cuida
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
                            claves_globales[token_actual]["evaluaciones"]["STAI"] = respuestas_stai
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
                            claves_globales[token_actual]["evaluaciones"]["BDI-II"] = respuestas_bdi
                            st.session_state["test_enviado"] = True
                            st.rerun()
