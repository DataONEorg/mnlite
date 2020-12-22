'''
Implements the AccessRule ORM
'''

import enum
import ojson as json
import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.types
import opersist.models

class AllowedPermissions(enum.Enum):
    read = "read"
    write = "write"
    changePermission = "changePermission"

    @classmethod
    def fromString(cls, ov):
        v = ov.lower().strip()
        if v[0] == "r":
            return cls.read
        if v[0] == "w":
            return cls.write
        if v[0] == "c":
            return cls.changePermission
        raise ValueError("Unknown permission string: %s", ov)

    @classmethod
    def toString(cls, v):
        if v == cls.read:
            return "read"
        if v == cls.write:
            return "write"
        if v == cls.changePermission:
            return "changePermission"
        raise ValueError("Unknown permission value: %s", v)


accessrule_subject_table = sqlalchemy.Table(
    "accessrule_subject",
    opersist.models.Base.metadata,
    sqlalchemy.Column(
        "accessrule_id", sqlalchemy.Integer, sqlalchemy.ForeignKey("accessrule._id")
    ),
    sqlalchemy.Column(
        "subject", sqlalchemy.String, sqlalchemy.ForeignKey("subject.subject")
    ),
)

thing_accessrule_table = sqlalchemy.Table(
    "thing_accessrule",
    opersist.models.Base.metadata,
    sqlalchemy.Column(
        "thing_id", sqlalchemy.String, sqlalchemy.ForeignKey("thing.checksum_sha256")
    ),
    sqlalchemy.Column(
        "accessrule_id", sqlalchemy.Integer, sqlalchemy.ForeignKey("accessrule._id")
    ),
)


class AccessRule(opersist.models.Base):
    __tablename__ = "accessrule"
    _id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
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
    permission = sqlalchemy.Column(
        sqlalchemy.types.Enum(AllowedPermissions),
        default=AllowedPermissions.read,
        doc="Access rule permission, 'read' | 'write' | 'changePermission'",
    )
    subjects = sqlalchemy.orm.relationship("Subject", secondary=accessrule_subject_table)

    def asJsonDict(self):
        res = {
            "id": self._id,
            "permission": AllowedPermissions.toString(self.permission),
            "t": opersist.utils.datetimeToJsonStr(self.t),
            "t_mod": opersist.utils.datetimeToJsonStr(self.t_mod),
            "subjects": []
        }
        for s in self.subjects:
            res['subjects'].append(s.asJsonDict())
        return res


    def __repr__(self):
        return json.dumps(self.asJsonDict(), indent=2)




