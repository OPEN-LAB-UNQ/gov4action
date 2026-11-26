"""R-1 1.2: la migración suma dos controles sin tocar las evaluaciones anteriores y se puede deshacer."""
import importlib.util
import json
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine

RAIZ = Path(__file__).resolve().parents[1]


def _migracion():
    spec = importlib.util.spec_from_file_location("m_r1_v12", RAIZ / "alembic" / "versions" / "20261121_r1_v12.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _base(conn):
    conn.exec_driver_sql("""CREATE TABLE versiones_protocolo (id INTEGER PRIMARY KEY, codigo TEXT, version TEXT, nombre TEXT, tipo_objeto TEXT,
        descripcion TEXT, activo BOOLEAN, creado_en TEXT, model_policy TEXT, matriz_lentes TEXT)""")
    conn.exec_driver_sql("""CREATE TABLE definiciones_control (id INTEGER PRIMARY KEY, protocolo_id INTEGER, codigo TEXT, nombre TEXT, descripcion TEXT,
        lente TEXT, obligatorio BOOLEAN, criticidad TEXT, condicion_aplicabilidad TEXT, evidencia_requerida TEXT, orden INTEGER)""")
    conn.exec_driver_sql("CREATE TABLE evaluaciones_certificacion (id INTEGER PRIMARY KEY, protocolo_id INTEGER)")
    conn.exec_driver_sql("INSERT INTO versiones_protocolo VALUES (1, 'B-1', '1.2', 'B', 'informe', 'b', 1, 'x', '{}', '[]')")
    conn.exec_driver_sql("INSERT INTO versiones_protocolo VALUES (2, 'R-1', '1.1', 'R', 'proyecto_ia', 'Protocolo de prueba.', 1, 'x', '{}', '[]')")
    for i in range(1, 4):
        conn.exec_driver_sql(f"INSERT INTO definiciones_control VALUES ({i}, 2, 'R1-0{i}', 'c{i}', 'd{i}', NULL, 1, 'alta', NULL, NULL, {i})")
    conn.exec_driver_sql("INSERT INTO evaluaciones_certificacion VALUES (1, 2)")


def test_la_migracion_agrega_la_version_12_y_deja_intacta_la_11():
    m = _migracion()
    assert m.down_revision == "20261104_equipos" and len(m.revision) <= 32
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        _base(conn)
        with Operations.context(MigrationContext.configure(conn)):
            m.upgrade()
            versiones = {(c, v): (i, a) for i, c, v, a in conn.exec_driver_sql("SELECT id, codigo, version, activo FROM versiones_protocolo")}
            assert versiones[("R-1", "1.2")][1] == 1 and versiones[("R-1", "1.1")][1] == 0 and versiones[("B-1", "1.2")][1] == 1
            nuevo = versiones[("R-1", "1.2")][0]
            codigos = [c for (c,) in conn.exec_driver_sql(f"SELECT codigo FROM definiciones_control WHERE protocolo_id={nuevo} ORDER BY orden")]
            assert codigos == ["R1-01", "R1-02", "R1-03", "R1-16", "R1-17"]
            evidencia = conn.exec_driver_sql(f"SELECT evidencia_requerida FROM definiciones_control WHERE protocolo_id={nuevo} AND codigo='R1-16'").scalar()
            assert "infiere_emociones" in json.loads(evidencia)["campos"]
            assert conn.exec_driver_sql("SELECT count(*) FROM definiciones_control WHERE protocolo_id=2").scalar() == 3  # la 1.1 no cambia
            assert conn.exec_driver_sql("SELECT protocolo_id FROM evaluaciones_certificacion").scalar() == 2  # la evaluación sigue en la 1.1
            assert "R1-16" in conn.exec_driver_sql(f"SELECT descripcion FROM versiones_protocolo WHERE id={nuevo}").scalar()
            m.downgrade()
            assert conn.exec_driver_sql("SELECT count(*) FROM versiones_protocolo WHERE codigo='R-1'").scalar() == 1
            assert conn.exec_driver_sql("SELECT activo FROM versiones_protocolo WHERE codigo='R-1'").scalar() == 1
            assert conn.exec_driver_sql("SELECT count(*) FROM definiciones_control").scalar() == 3
    engine.dispose()


def test_no_se_deshace_si_la_12_ya_tiene_evaluaciones():
    m = _migracion()
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        _base(conn)
        with Operations.context(MigrationContext.configure(conn)):
            m.upgrade()
            nuevo = conn.exec_driver_sql("SELECT id FROM versiones_protocolo WHERE codigo='R-1' AND version='1.2'").scalar()
            conn.exec_driver_sql(f"INSERT INTO evaluaciones_certificacion VALUES (2, {nuevo})")
            with pytest.raises(RuntimeError):
                m.downgrade()
    engine.dispose()


def test_la_migracion_y_los_datos_de_referencia_dicen_lo_mismo():
    m = _migracion()
    datos = json.loads((RAIZ / "sql" / "datos_referencia_protocolos.json").read_text(encoding="utf-8"))
    version = next(v for v in datos["versiones_protocolo"] if v["codigo"] == "R-1" and v["version"] == "1.2")
    por_codigo = {c["codigo"]: c for c in datos["definiciones_control"] if c["protocolo_id"] == version["id"]}
    for codigo, nombre, descripcion, evidencia, orden in m.NUEVOS:
        c = por_codigo[codigo]
        assert (c["nombre"], c["descripcion"], c["evidencia_requerida"], c["orden"]) == (nombre, descripcion, evidencia, orden)
    assert version["descripcion"].endswith(m.EXTRA)


def test_hay_una_sola_cabeza_de_migraciones():
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    assert ScriptDirectory.from_config(Config(str(RAIZ / "alembic.ini"))).get_heads() == ["20261126_retiro"]
