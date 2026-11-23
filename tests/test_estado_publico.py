import json

from fastapi.testclient import TestClient

from main import app
from services import estado_publico as ep


def test_estado_publico_no_expone_registros_privados(monkeypatch):
    monkeypatch.setattr(ep, '_cache', {})
    monkeypatch.setattr(ep, '_uso', lambda: {'informes': 4})
    monkeypatch.setattr(ep, '_prototipos', lambda: [])
    r = TestClient(app).get('/api/publico/estado')
    assert r.status_code == 200
    assert set(r.json()) == {'generado_en', 'actualizacion_segundos', 'versiones', 'uso', 'prototipos', 'validacion'}
    assert r.json()['uso']['datos'] == {'informes': 4}
    assert TestClient(app).get('/api/actividad').status_code == 401


def test_fallo_conserva_fecha_de_la_ultima_consulta(monkeypatch):
    monkeypatch.setattr(ep, '_cache', {})
    first = ep._fuente('test', lambda: [1])
    ep._cache['test']['vence'] = 0
    def fail():
        raise RuntimeError('no disponible')
    fallback = ep._fuente('test', fail)
    assert fallback['estado'] == 'ultima_copia'
    assert fallback['consultado_en'] == first['consultado_en']
    assert fallback['datos'] == [1]
    assert ep._fuente('sin-copia', fail)['estado'] == 'sin_datos'


def test_catalogo_permite_solo_campos_publicos():
    assert ep.limpiar_fichas([{'slug': '../login', 'titulo': 'x'},
        {'slug': 'caso-publico', 'titulo': 'Caso', 'email': 'privado', 'usuario_id': 10}]) == [
        {'slug': 'caso-publico', 'titulo': 'Caso', 'medicion': ''}]


def test_huella_detecta_interfaz_pero_no_evidencia_generada(tmp_path):
    (tmp_path/'static').mkdir()
    p = tmp_path/'static/index.html'
    p.write_text('uno')
    first = ep.huella(tmp_path)
    (tmp_path/'static/public-evidence.json').write_text('{}')
    assert ep.huella(tmp_path) == first
    p.write_text('dos')
    assert ep.huella(tmp_path) != first


def test_no_se_publica_evidencia_si_cambia_el_candidato(tmp_path):
    import pytest

    from scripts.evidencia_calidad import guardar
    with pytest.raises(RuntimeError, match='cambió'):
        guardar(tmp_path, tmp_path/'no-existe.xml', '', 'huella-distinta')


def test_evidencia_se_genera_desde_resultados_reales(tmp_path):
    from scripts.evidencia_calidad import guardar
    (tmp_path/'static').mkdir()
    junit = tmp_path/'resultado.xml'
    junit.write_text('<testsuites><testsuite><testcase name="a"/><testcase name="b"><skipped/></testcase></testsuite></testsuites>')
    fingerprint = ep.huella(tmp_path)
    guardar(tmp_path, junit, '# tests 3\n# pass 3\n# fail 0\n', fingerprint)
    result = json.loads((tmp_path/'static/public-evidence.json').read_text())
    assert result['tests']['passed'] == 1 and result['tests']['skipped'] == 1
    assert result['javascript']['passed'] == 3
    assert result['artifact_fingerprint'] == fingerprint


def test_paginas_del_proyecto_son_publicas():
    client = TestClient(app)
    for path, title in [("/estado", "Estado y evidencia"), ("/prototipos", "Proyectos, prototipos y planes de medición"), ("/investigacion", "Investigación y evidencia")]:
        response = client.get(path)
        assert response.status_code == 200
        assert title in response.text
    # El catálogo describe los proyectos; no promete acceso público a las demos.
    catalogo = client.get('/prototipos').text
    assert 'Las demostraciones requieren acceso autorizado.' in catalogo
    assert 'Los prototipos tienen acceso restringido' in catalogo
    assert client.get('/estado-proyecto.js').status_code == 200


def test_direccion_inexistente_muestra_404_sin_pedir_ingreso(monkeypatch):
    from core import auth
    monkeypatch.setattr(auth, 'active_token', lambda token: False)
    client = TestClient(app)
    response = client.get('/pagina-inexistente-revision', follow_redirects=False)
    assert response.status_code == 404
    assert 'No encontramos esa página' in response.text
    assert 'Volver al inicio' in response.text
    assert 'location' not in response.headers
    assert response.headers['x-robots-tag'] == 'noindex'
    assert client.head('/pagina-inexistente-revision').status_code == 404


def test_rutas_privadas_existentes_conservan_autenticacion(monkeypatch):
    from core import auth
    monkeypatch.setattr(auth, 'active_token', lambda token: False)
    client = TestClient(app)
    for path in ('/', '/index.html', '/app.js', '/index.html/'):
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 303
        assert response.headers['location'] == '/login'
    assert client.get('/api/actividad').status_code == 401
    assert client.get('/api/ruta-inexistente-revision').status_code == 401


def test_404_tambien_con_sesion_y_sin_servir_rutas_fuera_de_static(monkeypatch):
    from core import auth
    monkeypatch.setattr(auth, 'active_token', lambda token: True)
    client = TestClient(app)
    assert client.get('/pagina-inexistente-revision').status_code == 404
    response = client.get('/%2e%2e/config.py', follow_redirects=False)
    assert response.status_code == 404
    assert 'No encontramos esa página' in response.text
