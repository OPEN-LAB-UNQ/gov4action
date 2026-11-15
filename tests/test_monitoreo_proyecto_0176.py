"""0.10.76: en Monitoreo, lo propio de cada proyecto: su prototipo en acción y sus indicadores."""
import pytest
from test_calibracion_registro import entorno  # noqa: F401  (fixture reutilizada)

import models
from routers import monitoreo
from services import prototipos_incubadora as pi

PEDIR_REAL = pi._pedir_fichas  # el original: conftest lo reemplaza en cada prueba para no salir a la red
COM2 = "Grupo A · comisión 2"
FICHA = {"slug": "boletin-oficial", "medicion": "Control paralelo diario: normas detectadas y tiempo de lectura.",
         "medicion_ruta": "/boletin-oficial/control"}


@pytest.fixture
def proyecto(entorno, monkeypatch):  # noqa: F811
    db, _ = entorno
    db.add_all([
        models.Usuario(id=3, email="alumna@test", nombre="Alumna", password_hash="x", rol="analista", grupo=COM2),
        models.Usuario(id=4, email="alumno@test", nombre="Alumno", password_hash="x", rol="analista", grupo=COM2),
        models.Usuario(id=5, email="comision1@test", nombre="Uno", password_hash="x", rol="analista"),
    ])
    db.flush()
    p = models.ProyectoIA(id=66, usuario_id=3, titulo="Boletín",
                          situacion="Hoy la lectura diaria lleva dos horas. Queremos medir el tiempo de lectura antes y después.")
    sin_prototipo = models.ProyectoIA(id=500, usuario_id=4, titulo="Otro",
                                      situacion="Participantes importantes del área piden el reemplazo del sistema.")
    cartera = models.ProyectoIA(id=67, usuario_id=5, titulo="De la comisión 1", situacion="Vamos a medir el tiempo.")
    db.add_all([p, sin_prototipo, cartera])
    db.commit()
    monkeypatch.setattr(pi, "_fichas", lambda: {"boletin-oficial": dict(FICHA), "expedientes": dict(FICHA)})
    return db, p, sin_prototipo, cartera


def _usuario(db, ident):
    return db.get(models.Usuario, ident)


def _indicador(db, p, quien, titulo, valor):
    payload = {"tipo": "indicador", "titulo": titulo, "contenido": "Medido"}
    if valor is not None:
        payload["valor_indicador"] = valor
    monitoreo.registrar_monitoreo(p.id, payload, db, quien)


def test_monitoreo_muestra_el_prototipo_en_accion_y_como_mide(proyecto):
    db, p, _, _ = proyecto
    datos = monitoreo.listar_monitoreo(p.id, db, _usuario(db, 3))
    accion = datos["en_accion"]
    assert accion["url"] == "https://proyectos.entornodepruebas.com.ar/boletin-oficial/"
    assert accion["medicion_url"] == "https://proyectos.entornodepruebas.com.ar/boletin-oficial/control"
    assert accion["medicion_texto"] == FICHA["medicion"]
    assert datos["indicador_propuesto"] == "Queremos medir el tiempo de lectura antes y después."


def test_sin_prototipo_no_hay_bloque_y_una_palabra_suelta_no_se_toma_por_indicador(proyecto):
    db, _, sin_prototipo, _ = proyecto
    datos = monitoreo.listar_monitoreo(sin_prototipo.id, db, _usuario(db, 4))
    assert datos["en_accion"] is None
    assert datos["indicador_propuesto"] is None  # «participantes», «importantes» y «reemplazo» no cuentan
    assert datos["indicadores_registrados"] == [] and datos["por_tipo_etapa"] == {}


def test_en_cartera_no_se_calcula_nada_propio(proyecto):
    db, _, _, cartera = proyecto
    datos = monitoreo.listar_monitoreo(cartera.id, db, _usuario(db, 5))
    assert datos["modo"] == "cartera"
    assert datos["en_accion"] is None and datos["indicador_propuesto"] is None and datos["indicadores_registrados"] == []


def test_cada_indicador_muestra_su_ultimo_valor_el_anterior_y_cuantas_veces_se_midio(proyecto):
    db, p, _, _ = proyecto
    alumna = _usuario(db, 3)
    _indicador(db, p, alumna, "Minutos de lectura", 120)
    _indicador(db, p, alumna, "  minutos DE lectura ", 90)  # mismo indicador, escrito distinto
    _indicador(db, p, alumna, "Minutos de lectura", None)   # sin valor: no es una medición
    _indicador(db, p, alumna, "Normas detectadas", 7)
    monitoreo.registrar_monitoreo(p.id, {"tipo": "avance", "titulo": "Probé el control", "contenido": "Anduvo"}, db, alumna)
    datos = monitoreo.listar_monitoreo(p.id, db, alumna)
    kpis = {" ".join(k["titulo"].lower().split()): k for k in datos["indicadores_registrados"]}
    assert set(kpis) == {"minutos de lectura", "normas detectadas"}
    assert kpis["minutos de lectura"]["valor"] == 90 and kpis["minutos de lectura"]["anterior"] == 120
    assert kpis["minutos de lectura"]["mediciones"] == 2
    assert kpis["normas detectadas"]["valor"] == 7 and kpis["normas detectadas"]["anterior"] is None
    assert datos["por_tipo_etapa"] == {"indicador": 4, "avance": 1}


def test_los_indicadores_de_otra_etapa_no_se_mezclan(proyecto):
    db, p, _, _ = proyecto
    # un registro anterior a las etapas (sin etapa) no entra en los indicadores de la prueba
    db.add(models.RegistroMonitoreo(proyecto_id=p.id, usuario_id=3, tipo="indicador", titulo="Minutos de lectura",
                                    contenido="Viejo", estado="abierto", valor_indicador=999))
    db.commit()
    _indicador(db, p, _usuario(db, 3), "Minutos de lectura", 60)
    datos = monitoreo.listar_monitoreo(p.id, db, _usuario(db, 3))
    (kpi,) = datos["indicadores_registrados"]
    assert kpi["valor"] == 60 and kpi["anterior"] is None and kpi["mediciones"] == 1
    assert datos["por_tipo_etapa"] == {"indicador": 1}
    assert len(datos["registros"]) == 2  # el historial completo sigue a la vista


@pytest.mark.parametrize("ruta", ["https://otro.sitio/x", "/clubes/medicion", "/boletin-oficial/../admin",
                                  "/boletin-oficial/%2e%2e/admin", "/boletin-oficial/a?b", None, 42])
def test_la_direccion_de_medicion_solo_puede_ser_del_propio_prototipo(monkeypatch, ruta):
    monkeypatch.setattr(pi, "_fichas", lambda: {"boletin-oficial": {"slug": "boletin-oficial", "medicion_ruta": ruta}})
    accion = pi.en_accion(66)
    assert accion["medicion_url"] is None and accion["url"].endswith("/boletin-oficial/")


def test_si_el_sitio_no_responde_vale_la_ultima_copia_buena_y_se_reintenta_al_minuto(monkeypatch):
    reloj = [1000.0]
    monkeypatch.setattr(pi.time, "monotonic", lambda: reloj[0])
    respuestas = [[{"slug": "boletin-oficial", "medicion": "Mide", "medicion_ruta": "/boletin-oficial/control"}]]
    pedidos = []

    def pedir():
        pedidos.append(reloj[0])
        if respuestas:
            return respuestas.pop()
        raise OSError("caído")
    monkeypatch.setattr(pi, "_pedir_fichas", pedir)
    assert pi.en_accion(66)["medicion_texto"] == "Mide"          # primera copia buena
    reloj[0] += pi.FICHAS_VIGENCIA + 1
    assert pi.en_accion(66)["medicion_texto"] == "Mide"          # el sitio se cayó: vale la última copia buena
    reloj[0] += 30
    pi.en_accion(66)
    assert len(pedidos) == 2                                       # no vuelve a pedir enseguida
    reloj[0] += pi.FICHAS_REINTENTO
    pi.en_accion(66)
    assert len(pedidos) == 3                                       # al minuto, reintenta


def test_un_solo_pedido_a_la_vez(monkeypatch):
    llamadas = []
    monkeypatch.setattr(pi, "_pedir_fichas", lambda: llamadas.append(1) or [])
    assert pi._fichas_pidiendo.acquire(blocking=False)
    try:
        assert pi._fichas() == {} and llamadas == []  # otro pedido en curso: usa la copia y no espera
    finally:
        pi._fichas_pidiendo.release()


def test_el_pedido_real_va_a_la_red_local_con_tiempo_maximo(monkeypatch):
    pedidos = []

    class Respuesta:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'[{"slug": "boletin-oficial", "medicion": "Mide", "medicion_ruta": "/boletin-oficial/control"}]'

    def abrir(url, timeout):
        pedidos.append((url, timeout))
        return Respuesta()
    monkeypatch.setattr(pi.urllib.request, "urlopen", abrir)
    monkeypatch.setattr(pi, "_pedir_fichas", PEDIR_REAL)
    assert pi.en_accion(66)["medicion_url"].endswith("/boletin-oficial/control")
    assert pi.en_accion(66)["medicion_texto"] == "Mide"
    assert pedidos == [("http://127.0.0.1:6186/api/fichas", 1.5)]  # una vez: después vale la copia en memoria
