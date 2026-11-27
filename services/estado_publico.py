"""Información pública agregada; sin expedientes, usuarios ni textos privados."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_cache = {}
_lock = threading.Lock()


def huella(root=ROOT):
    """Incluye código, interfaz, portal, controles y documentación; no datos ni evidencia generada."""
    files = list(root.glob('*.py'))
    for folder in ('core', 'routers', 'services', 'static', 'scripts', 'tests', 'docs'):
        files.extend(p for p in (root / folder).rglob('*') if p.is_file()
                     and p.suffix in {'.py', '.js', '.cjs', '.html', '.css', '.json', '.md', '.png', '.jpg', '.svg', '.ico', '.woff2'}
                     and '__pycache__' not in p.parts and p.name != 'public-evidence.json')
    digest = hashlib.sha256()
    for p in sorted(set(files)):
        digest.update(str(p.relative_to(root)).encode())
        digest.update(b'\0')
        digest.update(p.read_bytes())
    return digest.hexdigest()


def _ahora():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _fuente(nombre, obtener, respaldo=None, fecha=None):
    now = time.monotonic()
    with _lock:
        old = _cache.get(nombre)
        if old and now < old['vence']:
            return dict(old['publico'])
        try:
            value = {'estado': 'actualizado', 'consultado_en': _ahora(), 'datos': obtener()}
            ttl = 300
        except Exception:
            value = dict(old['publico']) if old else {
                'datos': respaldo, 'consultado_en': fecha,
            }
            value['estado'] = 'ultima_copia' if value.get('datos') is not None else 'sin_datos'
            ttl = 60
        _cache[nombre] = {'vence': now + ttl, 'publico': value}
        return dict(value)


def _uso():
    from database import SessionLocal
    from services.uso_publico import calcular
    with SessionLocal() as db:
        return calcular(db)


def limpiar_fichas(items, sitio=None):
    if not isinstance(items, list):
        raise ValueError('Catálogo inválido')
    result = []
    for item in items[:200]:
        if not isinstance(item, dict):
            continue
        slug = item.get('slug', '')
        if not isinstance(slug, str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug):
            continue
        ficha = {'slug': slug, 'titulo': str(item.get('titulo', slug))[:200],
                 'medicion': str(item.get('medicion', ''))[:2000]}
        if sitio:  # el enlace lo arma Gov4Action con un sitio conocido, nunca con lo que llega en la ficha
            ficha['url'] = f'{sitio}/{slug}/'
        result.append(ficha)
    return result


def _prototipos():
    """Las fichas de los dos sitios de prototipos, cada una con su enlace. Si uno no responde, falla entera y queda la
    última copia completa: mejor que mostrar un catálogo incompleto como si estuviera al día."""
    from services import prototipos_incubadora as p
    result = []
    for url, sitio in ((p.FICHAS_URL, p.SITIO), (p.FICHAS_URL_GRUPO_B, p.SITIO_GRUPO_B)):
        with urllib.request.urlopen(url, timeout=2) as response:
            result += limpiar_fichas(json.loads(response.read(1024 * 1024)), sitio)
    return result


def estado():
    from versiones import ANALYSIS_VERSION, APP_VERSION, DOCUMENT_VERSION
    try:
        evidence = json.loads((ROOT / 'static/public-evidence.json').read_text())
    except (OSError, ValueError):
        evidence = {}
    fingerprint = _fuente('huella', huella)
    validation = {k: evidence[k] for k in ('tests', 'javascript', 'validado_en') if k in evidence}
    validation['vigente'] = bool(evidence.get('artifact_fingerprint') and
        fingerprint['estado'] == 'actualizado' and
        evidence['artifact_fingerprint'] == fingerprint['datos'])
    return {'generado_en': _ahora(), 'actualizacion_segundos': 300,
            'versiones': {'aplicacion': APP_VERSION, 'motor': ANALYSIS_VERSION, 'documento': DOCUMENT_VERSION},
            'uso': _fuente('uso', _uso, evidence.get('uso'), (evidence.get('uso') or {}).get('fecha')),
            'prototipos': _fuente('prototipos', _prototipos), 'validacion': validation}
