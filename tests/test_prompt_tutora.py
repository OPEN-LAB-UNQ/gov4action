"""El prompt de la tutora: voseo, y una versión para organizaciones que no se rompe en silencio."""
import re

from routers import proyectos_ia


def test_cada_reemplazo_de_organizaciones_encuentra_su_texto():
    for viejo, _ in proyectos_ia._PROMPT_ORGANIZACION:
        assert proyectos_ia.SYSTEM_PROMPT.count(viejo) == 1, viejo


def test_el_prompt_de_organizaciones_no_habla_de_administracion_publica(monkeypatch):
    monkeypatch.setattr(proyectos_ia.settings, "incubadora_ambito", "organizacion")
    texto = proyectos_ia.system_prompt_incubadora()
    assert "administración pública" not in texto and "empleados públicos" not in texto
    assert "en organizaciones" in texto


def test_imperativos_en_voseo():
    # Los imperativos sin tilde se leían como tuteo («Usa», «Trabaja», «Propone», «Hace»).
    for tuteo in ("Usa un tono", "Trabaja siempre", "Propone, cuando", "Hace como maximo", "Enfoca la conversacion", "Distingui siempre"):
        assert tuteo not in proyectos_ia.SYSTEM_PROMPT
    assert re.search(r"\bUsá un tono\b", proyectos_ia.SYSTEM_PROMPT)
    # Preguntas de afinado (tutoría del 10/10): opcionales, nunca un criterio nuevo.
    assert "no se copia en un fin de semana" in proyectos_ia.SYSTEM_PROMPT and "contra qué casos" in proyectos_ia.SYSTEM_PROMPT
    assert "podés sumar como OPCIONAL, de a una y sin convertirlas en requisito" in proyectos_ia.SYSTEM_PROMPT


def test_predevoluciones_guardadas_no_muestran_la_herramienta_personal_de_notas():
    from types import SimpleNamespace
    m = SimpleNamespace(id=1, proyecto_id=1, usuario_id=1, remitente="predevolucion_ia", creado_en=None,
                        contenido="Esta pre-devolución fue realizada íntegramente por inteligencia artificial, "
                                  "tomando como referencia las notas de Obsidian de Maximiliano Pérez.")
    salida = proyectos_ia._mensaje_out(m)["contenido"]
    assert "Obsidian" not in salida and "notas de orientación del docente responsable" in salida


def test_la_tutora_sabe_que_la_conversacion_queda_guardada():
    # 21/11/2026: dos veces dijo «cada sesión es independiente» y pidió copiar el chat; es falso.
    assert "quedan guardadas en su proyecto" in proyectos_ia.SYSTEM_PROMPT
    assert "Nunca digas que la sesión es independiente" in proyectos_ia.SYSTEM_PROMPT


def test_la_tutora_prefiere_preguntar_antes_que_ofrecerse_a_escribir():
    texto = proyectos_ia.SYSTEM_PROMPT
    assert "preferí una sola pregunta que ayude a pensar" in texto
    assert "No armes por tu cuenta ejemplos, listas de casos, planillas ni textos completos" in texto
    assert "no repitas el pedido" in texto and "no abras siempre con" in texto


def test_la_tutora_recuerda_que_los_datos_personales_son_ficticios_o_anonimizados():
    assert "DNI, CUIL, teléfono, fecha de nacimiento" in proyectos_ia.SYSTEM_PROMPT
    assert "ficticios o anonimizados" in proyectos_ia.SYSTEM_PROMPT


def test_las_reglas_nuevas_tambien_valen_para_organizaciones(monkeypatch):
    monkeypatch.setattr(proyectos_ia.settings, "incubadora_ambito", "organizacion")
    texto = proyectos_ia.system_prompt_incubadora()
    assert "quedan guardadas en su proyecto" in texto and "ficticios o anonimizados" in texto


def test_el_corrector_reemplaza_la_afirmacion_falsa_de_que_la_sesion_no_se_guarda():
    # Texto real de la tutora (20/11/2026), con una frase buena que debe conservarse.
    mala = ("Entiendo que querés saber si podés retomar esta conversación más adelante. En esta plataforma, cada sesión es independiente, "
            "por lo que no se guarda automáticamente el historial para futuras interacciones.\n\nTe recomiendo guardar localmente el texto de esta conversación.\n\n"
            "¿Qué punto del piloto querés definir ahora?")
    salida = proyectos_ia._corregir_guardado(mala)
    assert "independiente" not in salida and "guardar localmente" not in salida and "historial" not in salida
    assert salida.startswith(proyectos_ia.AVISO_GUARDADO) and "¿Qué punto del piloto querés definir ahora?" in salida


def test_el_corrector_no_toca_una_respuesta_normal():
    normal = "Tenés definido el problema. Guardá tu propuesta en «Entrega final» cuando quieras. ¿Qué riesgo falta precisar?"
    assert proyectos_ia._corregir_guardado(normal) == normal


def _capturar_mensajes(monkeypatch, pedido):
    import sys
    from types import SimpleNamespace

    from tests.test_avance_incubadora_052 import con_datos
    p = con_datos()
    recibido = {}

    def crear(**kwargs):
        recibido.update(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="Respuesta."), finish_reason="stop")])
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=crear)))
    monkeypatch.setattr(proyectos_ia.settings, "openai_api_key", "test-only")
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=lambda **kw: client))

    class DB:
        def query(self, *args): return self
        def filter(self, *args): return self
        def order_by(self, *args): return self
        def limit(self, *args): return self
        def all(self): return list(reversed(p.mensajes))
    proyectos_ia._respuesta_ia(DB(), p, pedido)
    return [m["content"] for m in recibido["messages"]], p


def test_la_conversacion_normal_cierra_el_contexto_con_el_recordatorio_de_forma(monkeypatch):
    pedido = "ahora pienso en el riesgo de los datos"
    textos, p = _capturar_mensajes(monkeypatch, pedido)
    esperado = proyectos_ia.RECORDATORIO_SIN_PREGUNTA if proyectos_ia._sin_preguntas(p, pedido) else proyectos_ia.RECORDATORIO_FORMA
    assert textos[-1] == esperado


def test_si_no_se_permiten_preguntas_el_recordatorio_no_las_pide():
    assert "cerrá con una sola pregunta" in proyectos_ia.RECORDATORIO_FORMA
    assert "no cierres con preguntas" in proyectos_ia.RECORDATORIO_SIN_PREGUNTA
    assert "cerrá con una sola pregunta" not in proyectos_ia.RECORDATORIO_SIN_PREGUNTA
    for texto in (proyectos_ia.RECORDATORIO_FORMA, proyectos_ia.RECORDATORIO_SIN_PREGUNTA):
        assert "nunca digas que la sesión es independiente" in texto and "ficticios o anonimizados" in texto


def test_no_queda_un_encabezado_colgado_cuando_se_quitan_las_preguntas():
    colgado = "Tu proyecto ya tiene el problema claro.\n\nPara avanzar,"
    assert proyectos_ia._ENCABEZADO_COLGADO.sub("", colgado).rstrip() == "Tu proyecto ya tiene el problema claro."
    otro = "Quedó definido el rol de la IA. Para seguir ordenando,"
    assert proyectos_ia._ENCABEZADO_COLGADO.sub("", otro).rstrip() == "Quedó definido el rol de la IA."
    normal = "Para avanzar, definí el indicador antes y después."
    assert proyectos_ia._ENCABEZADO_COLGADO.sub("", normal) == normal
    completa = "Tenés tres pendientes: el rol de la IA, los datos y el indicador."
    assert proyectos_ia._ENCABEZADO_COLGADO.sub("", completa) == completa


def test_la_sintesis_y_el_borrador_no_llevan_el_recordatorio_de_forma(monkeypatch):
    for pedido in ("Resumí el caso", "generá el borrador de la propuesta"):
        textos, _ = _capturar_mensajes(monkeypatch, pedido)
        assert proyectos_ia.RECORDATORIO_FORMA not in textos and proyectos_ia.RECORDATORIO_SIN_PREGUNTA not in textos


def test_la_tutora_senala_una_vez_los_usos_que_los_marcos_regulan_o_prohiben():
    texto = proyectos_ia.SYSTEM_PROMPT
    assert "inferir emociones o estados de ánimo de personas" in texto and "datos biométricos (rostro, voz, huellas)" in texto
    assert "señalalo una sola vez, en una línea" in texto and "No des una opinión legal" in texto
    for recordatorio in (proyectos_ia.RECORDATORIO_FORMA, proyectos_ia.RECORDATORIO_SIN_PREGUNTA):
        assert "inferir emociones de personas, puntuarlas o usar datos biométricos" in recordatorio
