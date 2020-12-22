"""
Implements the Subject ORM
"""

import ojson as json
import sqlalchemy
import sqlalchemy.orm
import opersist.models


class Subject(opersist.models.Base):
    __tablename__ = "subject"
    subject = sqlalchemy.Column(
        sqlalchemy.String, primary_key=True, doc="Subject string"
    )
    name = sqlalchemy.Column(sqlalchemy.String, index=True, doc="Name of subject")
    t = sqlalchemy.Column(
        sqlalchemy.DateTime(timezone=True),
        default=opersist.utils.dtnow,
        doc="When this entry was added to this datastore, UTC datetime",
    )
    t_mod = sqlalchemy.Column(
        sqlalchemy.DateTime(timezone=True),
        default=opersist.utils.dtnow,
        onupdate=opersist.utils.dtnow,
        doc="When this entry was modified in this datastore, UTC datetime",
    )

    def asJsonDict(self):
        return {
            "subject": self.subject,
            "name": self.name,
            "t": opersist.utils.datetimeToJsonStr(self.t),
            "t_mod": opersist.utils.datetimeToJsonStr(self.t),
        }

    def __repr__(self):
        return json.dumps(self.asJsonDict(), indent=2)
