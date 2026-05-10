from .init_dotenv import init_dotenv
from .init_sqlalchemy import SessionLocal, db, init_databases, ma


def init_plugs(app=None) -> None:
    init_dotenv()
    init_databases(app)
