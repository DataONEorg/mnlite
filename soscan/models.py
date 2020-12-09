import logging
import json
import sqlalchemy
import sqlalchemy.ext.declarative
import sqlalchemy.dialects.postgresql
import sqlalchemy.orm
import soscan.utils

_L = logging.getLogger("soscan.models")

Base = sqlalchemy.ext.declarative.declarative_base()


class SOContent(Base):

    __tablename__ = "socontent"

    url = sqlalchemy.Column(
        sqlalchemy.String,
        primary_key=True,
        doc="URL from which the SO content was retrieved",
    )
    time_loc= sqlalchemy.Column(
        sqlalchemy.DateTime(timezone=True),
        default=None,
        nullable=True,
        doc="Loc timestamp in sitemap",
    )
    time_modified = sqlalchemy.Column(
        sqlalchemy.DateTime(timezone=True),
        default=None,
        nullable=True,
        doc="Modification time reported in response header",
    )
    time_retrieved = sqlalchemy.Column(
        sqlalchemy.DateTime(timezone=True),
        default=soscan.utils.dtnow,
        doc="When the SO content was retrieved",
    )
    http_status = sqlalchemy.Column(
        sqlalchemy.Integer, default=0, doc="HTTP response status code"
    )
    jsonld = sqlalchemy.Column(
        sqlalchemy.dialects.postgresql.JSONB,
        nullable=True,
        default=None,
        doc="Array of extracted JSON-LD content",
    )

    def __repr__(self):
        return json.dumps(self.asJsonDict(), indent=2)

    def asJsonDict(self):
        return {
            "url": self.url,
            "time_retrieved": soscan.utils.datetimeToJsonStr(self.time_retrieved),
            "time_loc":soscan.utils.datetimeToJsonStr(self.time_loc),
            "time_modified":soscan.utils.datetimeToJsonStr(self.time_modified),
            "http_status": self.http_status,
            "jsonld": self.jsonld,
        }


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
    Session = sqlalchemy.orm.sessionmaker(bind=engine)
    session = Session()
    return session
