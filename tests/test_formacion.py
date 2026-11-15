import re
from pathlib import Path

from fastapi.testclient import TestClient

from main import app


def test_formacion_publica_y_compatible_con_csp():
    client=TestClient(app)
    for path in ('/formacion','/formacion/autoevaluacion','/formacion/mapa'):
        response=client.get(path)
        assert response.status_code==200
        assert '/gov4action-logo.png' in response.text
        assert 'economia.entornodepruebas' not in response.text
        assert not re.search(r'<script(?![^>]*\bsrc=)[^>]*>\s*\S',response.text)
        for asset in re.findall(r'(?:src|href)="(/formacion-assets/[^"]+)"',response.text):
            assert client.get(asset).status_code==200,asset
    assert client.get('/formacion-assets/knowledge-map.json').status_code==200
    assert client.get('/api/actividad').status_code==401
    assert client.get('/formacion-assets/no-autorizado.json',follow_redirects=False).status_code!=200

def test_portada_conserva_secciones_y_agrega_formacion_despues_de_herramientas():
    html=(Path(__file__).resolve().parents[1]/'static/portal/index.html').read_text(encoding='utf-8')
    assert html.index('id="herramientas"')<html.index('id="formacion"')<html.index('id="criterio"')
    for name in ('que-es','herramientas','criterio','respaldo'):
        assert html.count('id="'+name+'"')==1
