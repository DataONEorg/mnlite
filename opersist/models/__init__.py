import logging
import sqlalchemy
import sqlalchemy.ext.declarative
import sqlalchemy.orm
import sqlalchemy.exc
import sqlalchemy.schema
import sqlalchemy.ext.compiler
import sqlalchemy.types
import sqlalchemy.dialects.postgresql

__all__ = [
    "request",
    "relation",
    "identifier",
    "relation",
    "subject",
    "accessrule",
    "thing",
    "crawlstatus",
]

_L = logging.getLogger("opersist.models")

Base = sqlalchemy.ext.declarative.declarative_base()


# Use the JSONB type when connected to a postgres database
@sqlalchemy.ext.compiler.compiles(sqlalchemy.types.JSON, "postgresql")
def compile_binary_sqlite(type_, compiler, **kw):
    return "JSONB"


# Use STRING for storing UUIDs in sqlite
@sqlalchemy.ext.compiler.compiles(sqlalchemy.dialects.postgresql.UUID, "sqlite")
def compile_binary_sqlite(type_, compiler, **kw):
    return "STRING"


def createAll(engine):
    """
    Create the database tables etc if not aleady present.

    Args:
        engine: SqlAlchemy engine to use.

    Returns:
        nothing
    """
    Base.metadata.create_all(engine)


def getEngine(db_connection):
    engine = sqlalchemy.create_engine(db_connection)
    createAll(engine)
    return engine


def getSession(engine):
    session = sqlalchemy.orm.scoped_session(
        sqlalchemy.orm.sessionmaker(autocommit=False, autoflush=False, bind=engine)
    )
    # session = Session()
    return session
