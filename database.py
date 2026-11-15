from collections.abc import Generator

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db(request: Request) -> Generator[Session, None, None]:
    db = SessionLocal()
    # 0.10.74: en la vista «ver como» (la marca el middleware) nada se guarda. Lo que una pantalla escribe al
    # abrirse —crear el proyecto que falta, marcar el uso de Conexiones— queda en la transacción del pedido y se
    # deshace al terminar, así la cuenta administradora ve lo mismo que el participante sin dejar rastro a su nombre.
    solo_lectura = getattr(request.state, "ver_como", None) is not None
    if solo_lectura:
        db.commit = db.flush
    try:
        yield db
    finally:
        if solo_lectura:
            db.rollback()
        db.close()
