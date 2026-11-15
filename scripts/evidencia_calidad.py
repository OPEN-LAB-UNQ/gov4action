"""Publica evidencia sólo después de aprobar todos los controles aislados."""
import datetime as dt
import json
import os
import re
import xml.etree.ElementTree as ET


def guardar(root, junit, node_output, fingerprint):
    from services.estado_publico import huella
    from versiones import version_codigo
    if huella(root) != fingerprint:
        raise RuntimeError('El candidato cambió durante la validación; no publicar')
    cases = ET.parse(junit).getroot().findall('.//testcase')
    failed = sum(c.find('failure') is not None or c.find('error') is not None for c in cases)
    skipped = sum(c.find('skipped') is not None for c in cases)
    xfailed = sum(c.find('skipped') is not None and c.find('skipped').get('type') == 'pytest.xfail' for c in cases)
    total = re.search(r'^# tests (\d+)\s*$', node_output, re.M)
    passed = re.search(r'^# pass (\d+)\s*$', node_output, re.M)
    failures = re.search(r'^# fail (\d+)\s*$', node_output, re.M)
    if not cases or failed or not total or not passed or not failures or int(failures[1]):
        raise RuntimeError('Evidencia de controles incompleta o fallida')
    path = root / 'static/public-evidence.json'
    data = json.loads(path.read_text()) if path.exists() else {}
    now = dt.datetime.now(dt.timezone.utc)
    data.update(tests={'date': now.astimezone(dt.timezone(dt.timedelta(hours=-3))).strftime('%d/%m/%Y'),
                      'collected': len(cases), 'passed': len(cases)-failed-skipped,
                      'failed': failed, 'skipped': skipped-xfailed, 'xfailed': xfailed},
                javascript={'collected': int(total[1]), 'passed': int(passed[1]), 'failed': 0},
                validado_en=now.isoformat(), code_fingerprint=version_codigo(), artifact_fingerprint=fingerprint)
    temp = path.with_suffix('.json.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    os.replace(temp, path)
