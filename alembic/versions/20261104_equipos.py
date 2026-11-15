"""Proyectos en equipo de la Incubadora: tabla integrantes_proyecto_ia (0.10.67).

Tabla nueva: los proyectos existentes siguen siendo de una persona y nada se borra. Quien abrió el proyecto
sigue en proyectos_ia.usuario_id; cada persona que suma ocupa una fila, y una persona integra a lo sumo un
equipo ajeno.
"""
import sqlalchemy as sa

from alembic import op

revision = "20261104_equipos"
down_revision = "20261029_grupos"
branch_labels = depends_on = None


def upgrade():
    op.create_table(
        "integrantes_proyecto_ia",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("proyecto_id", sa.Integer(), sa.ForeignKey("proyectos_ia.id"), nullable=False),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("agregado_por_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=True),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("usuario_id", name="uq_integrante_proyecto_ia_usuario"),
    )
    op.create_index("ix_integrantes_proyecto_ia_proyecto_id", "integrantes_proyecto_ia", ["proyecto_id"])


def downgrade():
    op.drop_index("ix_integrantes_proyecto_ia_proyecto_id", table_name="integrantes_proyecto_ia")
    op.drop_table("integrantes_proyecto_ia")
