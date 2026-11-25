"""Los proyectos del grupo B enlazan su prototipo, en el sitio gemelo (24/11/2026)."""
from types import SimpleNamespace

from services import prototipos_incubadora as pi


def test_tabla_de_grupo_b():
    assert len(pi.PROTOTIPOS_GRUPO_B) == 32
    assert len(set(pi.PROTOTIPOS_GRUPO_B.values())) == 32
    assert not set(pi.PROTOTIPOS_GRUPO_B) & set(pi.PROTOTIPOS)
    assert not {117, 120, 122} & set(pi.PROTOTIPOS_GRUPO_B)  # sin contenido: sin prototipo
    assert pi.de(79)["url"] == "https://proyectos-grupo-b.example.org/lotes-de-informacion-salarial/"
    assert pi.de(66)["url"].startswith(pi.SITIO + "/")
    assert pi.de(117) is None
    assert {i for ids in pi.BASES_GRUPO_B.values() for i in ids} == set(pi.PROTOTIPOS_GRUPO_B)
    assert set(pi.BASES_GRUPO_B) <= {clave for clave, _, _ in pi.BASES}


def test_la_medicion_sale_del_sitio_de_grupo_b(monkeypatch):
    slug = pi.PROTOTIPOS_GRUPO_B[81]
    ficha = {"slug": slug, "medicion": "Mide", "medicion_ruta": f"/{slug}/medicion"}
    monkeypatch.setattr(pi, "_pedir_fichas_grupo_b", lambda: [ficha])
    accion = pi.en_accion(81)
    assert accion["medicion_url"] == f"{pi.SITIO_GRUPO_B}/{slug}/medicion"
    assert accion["medicion_texto"] == "Mide"
    assert pi.en_accion(66)["medicion_url"] is None  # el otro sitio no respondió: no se mezclan las copias


def test_conexiones_de_grupo_b_usan_su_sitio():
    r = pi.conexiones([SimpleNamespace(id=i, titulo="") for i in (81, 84, 88)])
    urls = [c["url"] for b in r["bases"] for c in b["casos"]]
    assert len(urls) == 3 and all(u.startswith(pi.SITIO_GRUPO_B + "/") for u in urls)
    assert r["componentes"] == []
