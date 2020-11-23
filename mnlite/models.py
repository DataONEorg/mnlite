"""
Tables:

  Relation
    subject
    predicate
    object
    context

  Content
    identifier
    size_bytes
    date_added
    date_modified
    checksum_md5
    checksum_sha1
    content

    format_id
    date_modified
    serial_version
    series_id
    submitter_id -> Subject._id
    rights_holder_id -> Subject_id
    access_policy_id -> AccessPolicy._id
    number_replicas
    replication_allowed
    replication_policy_id -> ReplicationPolicy._id
    archived
    date_uploaded
    origin_member_node
    obsoletes?
    obsoleted_by?
    media_type_name?
    file_name?

  AccessPolicy
    _id
    subject_id -> Subject._id
    permission

  Subjects
    _id
    subject

  LogRecord
    entry_id
    identifier
    ip_address
    user_agent
    subject -> Subject._id
    event
    date_logged
    node_id
"""

import json
import sqlalchemy
import sqlalchemy.ext.declarative

Base = sqlalchemy.ext.declarative.declarative_base()
from . import util


class Relation(Base):
    __tablename__ = "relation"
    s = sqlalchemy.Column(
        sqlalchemy.String, primary_key=True, doc="subject of statement"
    )
    p = sqlalchemy.Column(sqlalchemy.String, index=True, doc="predicate of statement")
    o = sqlalchemy.Column(sqlalchemy.String, index=True, doc="object of statement")
    context = sqlalchemy.Column(
        sqlalchemy.String, nullable=True, index=True, doc="context of statement"
    )

    def asJsonDict(self):
        res = {"s": self.s, "p": self.p, "o": self.o, "c": self.context}
        return res

    def __repr__(self):
        return json.dumps(self.asJsonDict(), indent=2)


class Subject(Base):
    __tablename__ = "subject"
    _id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    subject = sqlalchemy.Column(sqlalchemy.String, doc="Subject string")

    def asJsonDict(self):
        return {"id": self._id, "subject": self.subject}

    def __repr__(self):
        return json.dumps(self.asJsonDict(), indent=2)


class AccessPolicy(Base):
    __tablename__ = "accesspolicy"
    _id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    permission = sqlalchemy.Column(
        sqlalchemy.String(),
        default="read",
        doc="Access policy permission, 'read' | 'write' | 'changePermission'",
    )


class Content(Base):
    __tablename__ = "content"
    identifier = sqlalchemy.Column(
        sqlalchemy.String, primary_key=True, doc="Persistent identifier for object"
    )
    size_bytes = sqlalchemy.Column(
        sqlalchemy.Integer, nullable=False, doc="Size in bytes of the content"
    )
    date_added = sqlalchemy.Column(
        sqlalchemy.DateTime(timezone=True),
        doc="When the content was added to the database",
    )
    date_content_modified = sqlalchemy.Column(
        sqlalchemy.DateTime(timezone=True), doc="When the content was modified"
    )
    checksum_md5 = sqlalchemy.Column(
        sqlalchemy.String, nullable=False, doc="MD5 checksum of the content"
    )
    checksum_sha1 = sqlalchemy.Column(
        sqlalchemy.String, nullable=False, doc="SHA1 checksum of the content"
    )
    content = sqlalchemy.Column(
        sqlalchemy.JSON,
        nullable=False,
        doc="The JSON-LD content, normalized for consistent checksum",
    )
    # format_id
    format_id = sqlalchemy.Column(
        sqlalchemy.String, indexed=True, nullable=False, doc="DataONE format_id"
    )
    # date_modified
    date_modified = sqlalchemy.Column(
        sqlalchemy.DateTime(timezone=True),
        index=True,
        doc="When the content was modified",
    )
    # serial_version
    serial_version = sqlalchemy.Column(sqlalchemy.Integer, doc="sys metadata series id")
    # series_id
    series_id = sqlalchemy.Column(
        sqlalchemy.String, index=True, doc="Series identifier"
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
        sqlalchemy.ARRAY(sqlalchemy.String),
        doc="NodeIds of preferred replication targets",
    )
    # replication_blocked
    replication_blocked = sqlalchemy.Column(
        sqlalchemy.ARRAY(sqlalchemy.String),
        doc="NodeIds of blocked replication targets",
    )
    # archived
    archived = sqlalchemy.Column(sqlalchemy.Boolean, default=False, doc="Archive flag")
    # date_uploaded
    date_uploaded = sqlalchemy.Column(
        sqlalchemy.DateTime(timezone=True),
        doc="When the content was added to the DataONE system",
    )
    authoritative_member_node = sqlalchemy.Column(
        sqlalchemy.String, doc="Member node authoritative for this content"
    )
    # origin_member_node
    origin_member_node = sqlalchemy.Column(
        sqlalchemy.String, doc="Member node this content originated from"
    )
    # obsoletes?
    obsoletes = sqlalchemy.Column(
        sqlalchemy.String, nullable=True, index=True, doc="identifier of object this revision obsoletes"
    )
    # obsoleted_by?
    obsoleted_by = sqlalchemy.Column(
        sqlalchemy.String, nullable=True, index=True, doc="identifier of object obsoleting this object"
    )
    # media_type_name?
    media_type_name = sqlalchemy.Column(
        sqlalchemy.String, nullable=True, index=True, doc="Media type (mime type) of this thing"
    )
    # file_name?
    file_name = sqlalchemy.Column(
        sqlalchemy.String, nullable=True, index=True, doc="Original file name of this thing"
    )
    # submitter_id -> Subject._id
    # rights_holder_id -> Subject_id
    # access_policy_id -> AccessPolicy._id

    def asJsonDict(self):
        res = {
            "identifier": self.identifier,
            "size_bytes": self.size_bytes,
            "date_added": util.datetimeToJsonStr(self.date_added),
            "date_content_modified": util.datetimeToJsonStr(self.date_content_modified),
            "date_modified": util.datetimeToJsonStr(self.date_modified),
            "date_uploaded": util.datetimeToJsonStr(self.date_uploaded),
            "checksum_md5": self.checksum_md5,
            "checksum_sha1": self.checksum_sha1,
            "format_id": self.format_id,
            "serial_version": self.serial_version,
            "series_id":self.series_id,
            "replication_allowed": self.replication_allowed,
            "number_replicas": self.number_replicas,
            "replication_preferred": self.replication_preferred,
            "replicaiton_blocked": self.replication_blocked,
            "archived": self.archived,
            "authoritative_member_node": self.authoritative_member_node,
            "origin_member_node": self.origin_member_node,
            "obsoletes": self.obsoletes,
            "obsoleted_by": self.obsoleted_by,
            "media_type_name": self.media_type_name,
            "file_name": self.file_name,
            "content": self.content,
        }
        return res

    def __repr__(self):
        o = self.asJsonDict()
        return json.dumps(o, indent=2)
