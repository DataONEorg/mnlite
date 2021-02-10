import ojson as json
import sqlalchemy
import opersist.utils
import opersist.models


class Identifier(opersist.models.Base):
    """
    An identifier is used to reference things. This table
    holds information about identifiers, not the things they
    reference.

    Some identifiers may be used to reference many things
    (e.g. a series_id in DataONE). Others can reference
    one thing only.

    Where iden
    """

    __tablename__ = "identifier"

    _id = sqlalchemy.Column(
        sqlalchemy.Integer,
        primary_key=True,
        autoincrement=True,
        doc="Unique id for row.",
    )
    id = sqlalchemy.Column(
        sqlalchemy.String,
        index=True,
        doc="The identifier value",
    )
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
    source = sqlalchemy.Column(
        sqlalchemy.String, default="Manual", doc="The source of the identifier."
    )
    provider_id = sqlalchemy.Column(
        sqlalchemy.String,
        nullable=True,
        doc="The provider internal id, e.g. OAI-PMH record id.",
    )
    provider_time = sqlalchemy.Column(
        sqlalchemy.DateTime(timezone=True),
        nullable=True,
        doc="Timestamp reported for identifier provider entry if available, UTC datetime",
    )
    id_time = sqlalchemy.Column(
        sqlalchemy.DateTime(timezone=True),
        nullable=True,
        doc="Time reported in the record submitted or registered log event, UTC datetime",
    )
    registrant = sqlalchemy.Column(
        sqlalchemy.String,
        nullable=True,
        doc="Registrant name reported in the source record",
    )
    related = sqlalchemy.Column(
        sqlalchemy.JSON,
        nullable=True,
        default=None,
        doc="Related identifiers reported in the source record",
    )
    log = sqlalchemy.Column(
        sqlalchemy.JSON,
        nullable=True,
        default=None,
        doc="log entries in source record",
    )
    set_spec = sqlalchemy.Column(
        sqlalchemy.JSON,
        nullable=True,
        default=None,
        doc="Set labels, e.g. OAI-PMH set names",
    )

    def asJsonDict(self):
        """
        Provide a JSON serializable dict representation of instance.

        Returns:
            dict
        """
        d = {
            "_id": self._id,
            "id": self.id,
            "t": opersist.utils.datetimeToJsonStr(self.t),
            "t_mod": opersist.utils.datetimeToJsonStr(self.t),
            "source": self.source,
            "provider_id": self.provider_id,
            "service_id": self.service_id,
            "provider_time": opersist.utils.datetimeToJsonStr(self.provider_time),
            "id_time": opersist.utils.datetimeToJsonStr(self.id_time),
            "registrant": self.registrant,
            "related": self.related,
            "log": self.log,
            "sets": self.set_spec,
        }
        return d

    def __repr__(self):
        return json.dumps(self.asJsonDict(), indent=2)
