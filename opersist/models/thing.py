import logging
import os
import time
import ojson as json
import dateparser
import sqlalchemy
import sqlalchemy.ext.declarative
import sqlalchemy.orm
import sqlalchemy.exc
import sqlalchemy.event
import opersist.models
import opersist.models.accessrule

DEFAULT_FORMATID = "application/octet-stream"


class Thing(opersist.models.Base):

    __tablename__ = "thing"

    checksum_sha256 = sqlalchemy.Column(
        sqlalchemy.String,
        primary_key=True,
        doc="sha256 hash of content used as primary key",
    )
    identifier = sqlalchemy.Column(
        sqlalchemy.String,
        index=True,
        nullable=True,
        unique=True,
        default=None,
        doc="Persistent identifier for thing. Must be unique if set.",
    )
    series_id = sqlalchemy.Column(
        sqlalchemy.String,
        index=True,
        nullable=True,
        default=None,
        doc="Series identifier.",
    )
    size_bytes = sqlalchemy.Column(
        sqlalchemy.Integer, nullable=False, doc="Size in bytes of the content"
    )
    checksum_md5 = sqlalchemy.Column(
        sqlalchemy.String, nullable=False, doc="MD5 checksum of the content"
    )
    checksum_sha1 = sqlalchemy.Column(
        sqlalchemy.String, nullable=False, doc="SHA1 checksum of the content"
    )
    identifiers = sqlalchemy.Column(
        sqlalchemy.JSON,
        default=[],
        doc="List of other identifiers associated with this thing, not including PID or SID",
    )
    t_added = sqlalchemy.Column(
        sqlalchemy.DateTime(timezone=True),
        default=opersist.utils.dtnow,
        doc="When the content was added to the database",
    )
    t_content_modified = sqlalchemy.Column(
        sqlalchemy.DateTime(timezone=True),
        default=opersist.utils.dtnow,
        doc="When the content was modified. Should be equal or older than t_added",
    )
    # date_modified
    date_modified = sqlalchemy.Column(
        sqlalchemy.DateTime(timezone=True),
        index=True,
        default=opersist.utils.dtnow,
        doc="When this record was modified, like system metadata date modified",
    )
    # date_uploaded
    date_uploaded = sqlalchemy.Column(
        sqlalchemy.DateTime(timezone=True),
        nullable=True,
        default=opersist.utils.dtnow,
        doc="When the content was added to the DataONE system",
    )
    content = sqlalchemy.Column(
        sqlalchemy.String,
        nullable=False,
        doc="Relative path to the object described by this entry",
    )
    # media_type_name?
    media_type_name = sqlalchemy.Column(
        sqlalchemy.String,
        nullable=True,
        index=True,
        default="application/octet-stream",
        doc="Media type (mime type) of this thing",
    )
    # file_name?
    file_name = sqlalchemy.Column(
        sqlalchemy.String,
        nullable=True,
        index=True,
        doc="Original file name of this thing, excluding path",
    )
    source = sqlalchemy.Column(
        sqlalchemy.String,
        nullable=False,
        index=True,
        doc="Source of this thing, such as full path or URL"
    )
    # DataONE sysmetadata specific stuff
    format_id = sqlalchemy.Column(
        sqlalchemy.String,
        index=True,
        default="application/octet-stream",
        doc="DataONE formatId for thing",
    )
    # serial_version
    serial_version = sqlalchemy.Column(
        sqlalchemy.Integer, default=1, doc="sys metadata series id"
    )
    # replication_allowed
    replication_allowed = sqlalchemy.Column(
        sqlalchemy.Boolean, default=True, doc="Replication allowed for this thing"
    )
    # number_replicas
    number_replicas = sqlalchemy.Column(
        sqlalchemy.Integer, default=3, doc="Desired number of replicas"
    )
    # replication_preferred
    replication_preferred = sqlalchemy.Column(
        sqlalchemy.JSON(sqlalchemy.String),
        default=[],
        doc="NodeIds of preferred replication targets",
    )
    # replication_blocked
    replication_blocked = sqlalchemy.Column(
        sqlalchemy.JSON(sqlalchemy.String),
        default=[],
        doc="NodeIds of blocked replication targets",
    )
    # archived
    archived = sqlalchemy.Column(
        sqlalchemy.Boolean, index=True, default=False, doc="Archive flag"
    )
    authoritative_member_node = sqlalchemy.Column(
        sqlalchemy.String, index=True, doc="Member node authoritative for this content"
    )
    # origin_member_node
    origin_member_node = sqlalchemy.Column(
        sqlalchemy.String, index=True, doc="Member node this content originated from"
    )
    # obsoletes?
    obsoletes = sqlalchemy.Column(
        sqlalchemy.String,
        nullable=True,
        index=True,
        doc="identifier of object this revision obsoletes",
    )
    # obsoleted_by?
    obsoleted_by = sqlalchemy.Column(
        sqlalchemy.String,
        nullable=True,
        index=True,
        doc="identifier of object obsoleting this object",
    )
    # submitter_id -> Subject._id
    submitter_id = sqlalchemy.Column(
        sqlalchemy.Integer, sqlalchemy.ForeignKey("subject.subject")
    )
    submitter = sqlalchemy.orm.relationship("Subject", foreign_keys=[submitter_id])
    rights_holder_id = sqlalchemy.Column(
        sqlalchemy.Integer, sqlalchemy.ForeignKey("subject.subject")
    )
    rights_holder = sqlalchemy.orm.relationship(
        "Subject", foreign_keys=[rights_holder_id]
    )
    access_policy = sqlalchemy.orm.relationship(
        "AccessRule", secondary=opersist.models.accessrule.thing_accessrule_table
    )
    _meta = sqlalchemy.Column(
        sqlalchemy.JSON,
        nullable=True,
        default=None,
        doc="Additional information pertinent to this record",
    )
    __table_args__ = (
        sqlalchemy.CheckConstraint("identifier != series_id"),
    )

    @sqlalchemy.orm.validates("identifier", "series_id", "format_id")
    def validate_identifier(self, key, value):
        if value is not None:
            value = value.strip()
            if opersist.utils.stringHasSpace(value):
                raise ValueError(f"An identifier must not contain spaces: '{value}'")
            if key == 'series_id':
                if self.identifier is None:
                    raise ValueError(f"series_id can not be set without a persistent identifier")
        return value

    def asJsonDict(self):
        res = {
            "identifier": self.identifier,
            "series_id": self.series_id,
            "size_bytes": self.size_bytes,
            "checksum_sha256": self.checksum_sha256,
            "checksum_sha1": self.checksum_sha1,
            "checksum_md5": self.checksum_md5,
            "identifiers": self.identifiers,
            "t_added": opersist.utils.datetimeToJsonStr(self.t_added),
            "t_content_modified": opersist.utils.datetimeToJsonStr(
                self.t_content_modified
            ),
            "content": self.content,
            "media_type_name": self.media_type_name,
            "file_name": self.file_name,
            "format_id": self.format_id,
            "date_modified": opersist.utils.datetimeToJsonStr(self.date_modified),
            "date_uploaded": opersist.utils.datetimeToJsonStr(self.date_uploaded),
            "serial_version": self.serial_version,
            "replication_allowed": self.replication_allowed,
            "number_replicas": self.number_replicas,
            "replication_preferred": []
            if self.replication_preferred is None
            else self.replication_preferred,
            "replication_blocked": []
            if self.replication_blocked is None
            else self.replication_blocked,
            "archived": self.archived,
            "authoritative_member_node": self.authoritative_member_node,
            "origin_member_node": self.origin_member_node,
            "obsoletes": self.obsoletes,
            "obsoleted_by": self.obsoleted_by,
            "submitter": None
            if self.submitter is None
            else self.submitter.asJsonDict(),
            "rights_holder": None
            if self.rights_holder is None
            else self.rights_holder.asJsonDict(),
            "access_policy": [],
        }
        for ar in self.access_policy:
            res["access_policy"].append(ar.asJsonDict())
        return res

    def __str__(self):
        return json.dumps(self.asJsonDict(), indent="  ")

    def __repr__(self):
        return json.dumps(self.asJsonDict())


@sqlalchemy.event.listens_for(Thing, 'before_insert')
def doThingChecks(mapper, connect, target):
    logging.debug("At doThingChecks: %s", target)