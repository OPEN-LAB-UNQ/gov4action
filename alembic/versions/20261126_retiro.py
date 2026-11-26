"""Incubadora: quien abrió un proyecto puede dejarlo para sumarse a un equipo (columna proyectos_ia.retirado_en).

Columna nueva y vacía: ningún proyecto cambia al aplicarla. Dejar un proyecto no borra nada; sólo anota cuándo.
"""
import sqlalchemy as sa

from alembic import op

revision = "20261126_retiro"
down_revision = "20261121_r1_v12"
branch_labels = depends_on = None


def upgrade():
    op.add_column("proyectos_ia", sa.Column("retirado_en", sa.DateTime(), nullable=True))


def downgrade():
    # Quitar la columna perdería qué proyectos se dejaron: si hay alguno, hay que resolverlo antes.
    dejados = op.get_bind().execute(sa.text("select count(*) from proyectos_ia where retirado_en is not null")).scalar()
    if dejados:
        raise RuntimeError(f"Hay {dejados} proyecto(s) dejado(s): recuperalos antes de volver atrás.")
    op.drop_column("proyectos_ia", "retirado_en")
