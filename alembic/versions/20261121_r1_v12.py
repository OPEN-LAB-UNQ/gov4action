"""R-1 1.2: suma el filtro de prácticas prohibidas (R1-16) y la clasificación del nivel de riesgo (R1-17).

Las evaluaciones anteriores conservan su versión 1.1: no se reinterpretan."""
import json

import sqlalchemy as sa

from alembic import op

revision = "20261121_r1_v12"
down_revision = "20261104_equipos"
branch_labels = depends_on = None

EXTRA = ' La versión 1.2 suma el filtro de prácticas prohibidas (R1-16) y la clasificación del nivel de riesgo (R1-17).'
NUEVOS = [
    [
        "R1-16",
        "Filtro de prácticas prohibidas",
        "Descarta antes de seguir los usos que el marco aplicable prohíbe, como inferir emociones de estudiantes o trabajadores a partir de rasgos biométricos, puntuar socialmente a las personas, manipular o explotar vulnerabilidades o categorizar personas por rasgos sensibles con datos biométricos; si alguno aparece, el proyecto no continúa sin rediseño y revisión jurídica.",
        {
            "campos": [
                "uso_previsto",
                "infiere_emociones",
                "puntua_personas",
                "usa_datos_biometricos",
                "manipula_o_explota_vulnerabilidades",
                "resultado_del_filtro",
                "derivacion_juridica"
            ]
        },
        16
    ],
    [
        "R1-17",
        "Clasificación del nivel de riesgo",
        "Clasifica el uso (prohibido, alto, limitado o mínimo) según el marco que aplique de acuerdo con el mapa jurisdiccional, justifica el nivel y deja asentadas las obligaciones que se derivan, como avisar que se interactúa con IA; los usos que evalúan o deciden sobre personas se derivan a revisión jurídica. Orienta y no reemplaza el asesoramiento jurídico.",
        {
            "campos": [
                "marco_aplicable",
                "nivel",
                "justificacion",
                "obligaciones_derivadas",
                "aviso_de_ia_a_usuarios",
                "derivacion_juridica"
            ]
        },
        17
    ]
]


def upgrade():
    conn = op.get_bind()
    anterior = conn.execute(sa.text("SELECT id FROM versiones_protocolo WHERE codigo='R-1' AND version='1.1'")).scalar_one()
    conn.execute(sa.text("""INSERT INTO versiones_protocolo
        (codigo, version, nombre, tipo_objeto, descripcion, activo, creado_en, model_policy, matriz_lentes)
        SELECT codigo, '1.2', nombre, tipo_objeto, descripcion || :extra, :activo, CURRENT_TIMESTAMP, model_policy, matriz_lentes
        FROM versiones_protocolo WHERE id=:anterior"""), {"extra": EXTRA, "activo": True, "anterior": anterior})
    nuevo = conn.execute(sa.text("SELECT id FROM versiones_protocolo WHERE codigo='R-1' AND version='1.2'")).scalar_one()
    conn.execute(sa.text("""INSERT INTO definiciones_control
        (protocolo_id,codigo,nombre,descripcion,lente,obligatorio,criticidad,condicion_aplicabilidad,evidencia_requerida,orden)
        SELECT :nuevo,codigo,nombre,descripcion,lente,obligatorio,criticidad,condicion_aplicabilidad,evidencia_requerida,orden
        FROM definiciones_control WHERE protocolo_id=:anterior"""), {"nuevo": nuevo, "anterior": anterior})
    for codigo, nombre, descripcion, evidencia, orden in NUEVOS:
        conn.execute(sa.text("""INSERT INTO definiciones_control
            (protocolo_id,codigo,nombre,descripcion,lente,obligatorio,criticidad,condicion_aplicabilidad,evidencia_requerida,orden)
            VALUES (:nuevo,:codigo,:nombre,:descripcion,NULL,:obligatorio,'critica',NULL,:evidencia,:orden)"""),
            {"nuevo": nuevo, "codigo": codigo, "nombre": nombre, "descripcion": descripcion, "obligatorio": True,
             "evidencia": json.dumps(evidencia, ensure_ascii=False), "orden": orden})
    conn.execute(sa.text("UPDATE versiones_protocolo SET activo=:inactivo WHERE codigo='R-1' AND id<>:nuevo"), {"inactivo": False, "nuevo": nuevo})


def downgrade():
    conn = op.get_bind()
    nuevo = conn.execute(sa.text("SELECT id FROM versiones_protocolo WHERE codigo='R-1' AND version='1.2'")).scalar_one()
    if conn.execute(sa.text("SELECT count(*) FROM evaluaciones_certificacion WHERE protocolo_id=:id"), {"id": nuevo}).scalar():
        raise RuntimeError("R-1 1.2 ya tiene evaluaciones: no eliminar su versión histórica")
    conn.execute(sa.text("DELETE FROM definiciones_control WHERE protocolo_id=:id"), {"id": nuevo})
    conn.execute(sa.text("DELETE FROM versiones_protocolo WHERE id=:id"), {"id": nuevo})
    conn.execute(sa.text("UPDATE versiones_protocolo SET activo=:activo WHERE codigo='R-1' AND version='1.1'"), {"activo": True})
