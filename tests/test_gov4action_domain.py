from fastapi.testclient import TestClient

from config import settings
from core.auth import login_html, origen_confiable
from main import SITE_URL, app


def test_new_domain_and_old_origin_rejected():
    assert settings.public_base_url == "https://gov4action.com"
    assert SITE_URL == settings.public_base_url
    assert origen_confiable({"origin": "https://gov4action.com"})
    assert not origen_confiable({"origin": "https://gobernanza.entornodepruebas.com.ar"})
    assert not origen_confiable({"origin": "https://gov4action.com.evil.test"})

def test_new_login_brand_and_same_origin_form():
    html = login_html()
    assert "Gov4Action" in html
    assert 'action="/login"' in html
    assert 'href="/privacidad"' in html
    assert "entornodepruebas.com.ar" not in html
    client = TestClient(app)
    assert client.get("/api/me").status_code == 401
    assert client.post("/login", headers={"origin":"https://gobernanza.entornodepruebas.com.ar"}).status_code == 403
