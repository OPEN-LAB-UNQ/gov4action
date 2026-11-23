"""La instalación desde cero carga las definiciones vigentes de los protocolos."""
import json
from pathlib import Path

DATOS = Path(__file__).resolve().parents[1] / "sql" / "datos_referencia_protocolos.json"


def test_datos_de_referencia_tienen_los_protocolos_vigentes():
    datos = json.loads(DATOS.read_text(encoding="utf-8"))
    versiones = {(v["codigo"], v["version"]): v for v in datos["versiones_protocolo"]}
    activos = sorted((c, v) for (c, v), fila in versiones.items() if fila["activo"])
    assert activos == [("B-1", "1.2"), ("R-1", "1.2")]
    controles = {}
    for control in datos["definiciones_control"]:
        controles.setdefault(control["protocolo_id"], []).append(control["codigo"])
    assert len(controles[versiones[("B-1", "1.2")]["id"]]) == 11
    assert len(controles[versiones[("R-1", "1.1")]["id"]]) == 15  # la versión anterior queda intacta
    assert len(controles[versiones[("R-1", "1.2")]["id"]]) == 17
    for fila in datos["versiones_protocolo"]:
        assert isinstance(fila["model_policy"], dict)


def test_datos_de_referencia_no_traen_informacion_de_usuarios():
    datos = json.loads(DATOS.read_text(encoding="utf-8"))
    assert set(datos) == {"descripcion", "exportado", "versiones_protocolo", "definiciones_control"}
    texto = DATOS.read_text(encoding="utf-8")
    assert "@" not in texto


def test_requirements_incluye_alembic_para_instalar():
    requisitos = (DATOS.parents[1] / "requirements.txt").read_text(encoding="utf-8")
    assert any(linea.startswith("alembic==") for linea in requisitos.splitlines())


def test_r1_v12_suma_el_filtro_de_practicas_prohibidas_y_la_clasificacion_de_riesgo():
    datos = json.loads(DATOS.read_text(encoding="utf-8"))
    version = next(v for v in datos["versiones_protocolo"] if v["codigo"] == "R-1" and v["version"] == "1.2")
    controles = {c["codigo"]: c for c in datos["definiciones_control"] if c["protocolo_id"] == version["id"]}
    assert [c for c in controles if c in ("R1-16", "R1-17")] == ["R1-16", "R1-17"]
    for codigo in ("R1-16", "R1-17"):
        assert controles[codigo]["obligatorio"] is True and controles[codigo]["criticidad"] == "critica"
        assert controles[codigo]["evidencia_requerida"]["campos"]
    assert "infiere_emociones" in controles["R1-16"]["evidencia_requerida"]["campos"]
    assert "aviso_de_ia_a_usuarios" in controles["R1-17"]["evidencia_requerida"]["campos"]
    # los 15 controles anteriores se copian sin cambios
    anteriores = {c["codigo"]: c for c in datos["definiciones_control"]
                  if c["protocolo_id"] == next(v["id"] for v in datos["versiones_protocolo"] if v["codigo"] == "R-1" and v["version"] == "1.1")}
    for codigo, viejo in anteriores.items():
        assert controles[codigo]["descripcion"] == viejo["descripcion"] and controles[codigo]["criticidad"] == viejo["criticidad"]
