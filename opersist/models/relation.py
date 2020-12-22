"""
Implements the Relation ORM
"""

import ojson as json
import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.dialects.postgresql
import opersist.models
import opersist.utils


class Relation(opersist.models.Base):

    __tablename__ = "relation"

    id = sqlalchemy.Column(
        sqlalchemy.dialects.postgresql.UUID,
        default=opersist.utils.generateUUID,
        primary_key=True,
        doc="Generated UUID",
    )
    s = sqlalchemy.Column(sqlalchemy.String, index=True, doc="Subject of statement")
    p = sqlalchemy.Column(sqlalchemy.String, index=True, doc="Predicate of statement")
    o = sqlalchemy.Column(sqlalchemy.String, index=True, doc="Object of statement")
    c = sqlalchemy.Column(
        sqlalchemy.String, nullable=True, index=True, doc="Context of statement"
    )
    o_type = sqlalchemy.Column(
        sqlalchemy.String, index=True, doc="Type of the object referenced in statement"
    )
    t = sqlalchemy.Column(
        sqlalchemy.DateTime(timezone=True),
        default=opersist.utils.dtnow,
        doc="When this relation was recorded, UTC datetime",
    )
    t_mod = sqlalchemy.Column(
        sqlalchemy.DateTime(timezone=True),
        default=opersist.utils.dtnow,
        onupdate=opersist.utils.dtnow,
        doc="When this entry was modified in this datastore, UTC datetime",
    )

    def asJsonDict(self):
        res = {
            "id": self.id,
            "s": self.s,
            "p": self.p,
            "o": self.o,
            "c": self.c,
            "o_type": self.o_type,
            "t": opersist.utils.datetimeToJsonStr(self.t),
            "t_mod": opersist.utils.datetimeToJsonStr(self.t),
        }
        return res

    def __repr__(self):
        return json.dumps(self.asJsonDict(), indent=2)
