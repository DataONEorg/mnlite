import os
import logging
try:
    import orjson as json
except ModuleNotFoundError:
    import json

import tempfile
import sqlalchemy.exc
import sqlalchemy.orm.exc
import sqlalchemy.event
from . import utils
from . import flob
from . import models
from .models import subject
from .models import accessrule
from .models import thing
from time import sleep


DEFAULT_DATABASE = "sqlite:///content.db"
DEFAULT_STORE = "content"
"""
Folder structure is like:
some-folder/
  content/
    opersist.conf
    content.db  #if using sqlite
    data/
      a/ 
      ...
"""


class OPersist(object):

    CONFIG_FILE = "node.json"
    BLOB_PATH = "data"
    PUBLIC_SUBJECT = "public"
    PUBLIC_SUBJECT_NAME = "Anonymous user"

    def __init__(self, fs_path, db_url=None, config_file=CONFIG_FILE):
        self._L = logging.getLogger(self.__class__.__name__)
        self.fs_path = fs_path
        self.db_url = db_url if db_url is not None else DEFAULT_DATABASE
        self._path_root = os.path.abspath(fs_path)
        self._blob_path = os.path.join(self._path_root, OPersist.BLOB_PATH)
        self._conf_path = os.path.join(self._path_root, config_file)
        self._engine = None
        self._session = None
        self._ostore = None
        self._default_owner = None
        self._default_submitter = None

    def getConfig(self):
        if not os.path.exists(self._conf_path):
            return None
        conf = {}
        with open(self._conf_path, "r") as conf_src:
            conf = json.loads(conf_src.read())
        return conf

    def setConfig(self, conf):
        with open(self._conf_path, "w") as conf_dest:
            conf_dest.write(json.dumps(conf, indent=2))

    def _on_pickle(self, target, state_dict):
        self._L.debug("On pickle, target: %s", target)

    def open(self, allow_create=True):
        if self._engine is None:
            # Setup everything, possibly initializing
            os.makedirs(self._path_root, exist_ok=True)
            conf = self.getConfig()
            if conf is None:
                if allow_create:
                    conf = {
                        "data_folder": OPersist.BLOB_PATH,
                        "content_database": self.db_url,
                        "created": utils.datetimeToJsonStr(utils.dtnow()),
                        "default_submitter": None,
                        "default_owner": None,
                    }
                    self.setConfig(conf)
                else:
                    raise ValueError(f"No OPersist instance at {self._path_root}")
            with utils.pushd(self._path_root):
                self._engine = models.getEngine(conf["content_database"])
                self._session = models.getSession(self._engine)
                # sqlalchemy.event.listen(models.thing.Thing, 'pickle', self._on_pickle)
                self._ostore = flob.FLOB(conf["data_folder"])
            # Ensure the public subject is available
            subj = self.getPublicReadAccessRule()
        else:
            conf = self.getConfig()
            with utils.pushd(self._path_root):
                if self._session is None:
                    self._session = models.getSession(self._engine)
                    # sqlalchemy.event.listen(models.thing.Thing, 'pickle', self._on_pickle)
                if self._ostore is None:
                    self._ostore = flob.FLOB(conf["data_folder"])

    def getSession(self):
        assert self._session is not None
        return self._session

    def removeSession(self):
        pass
        # self.close()
        # print("Remove Session")
        # if not self._session is None:
        #    self._session.remove()

    def commit(self):
        self._session.flush()
        self._session.commit()

    def close(self):
        if not self._session is None:
            self._session.remove()
            # self._session.close()
            self._session = None
            self._engine = None
        if not self._ostore is None:
            self._ostore.close()
            self._ostore = None

    def getOrCreate(self, model, create_method="", create_method_kwargs=None, **kwargs):
        """
        Get or create and get a record.

        Find a record that matches a query on kwargs. Create the record if
        nothing matches. Return the found or created record.

        Args:
            session: sqlalchemy session
            model: the model (table) to work with
            create_method: The method to use for creating the record
            create_method_kwargs: kwargs to pass to the create method
            **kwargs: kwargs to query for an existing record

        Returns:
            tuple, (record, True if created)
        """
        assert self._session is not None
        try:
            return self._session.query(model).filter_by(**kwargs).one(), False
        except sqlalchemy.orm.exc.NoResultFound:
            kwargs.update(create_method_kwargs or {})
            created = getattr(model, create_method, model)(**kwargs)
            try:
                self._session.add(created)
                self.commit()
                return created, True
            except sqlalchemy.exc.IntegrityError:
                self._session.rollback()
                return self._session.query(model).filter_by(**kwargs).one(), False

    # ==================================
    # Subject operations
    def getSubject(self, subj, name=None, create_if_missing=False):
        assert self._session is not None
        s = self._session.query(subject.Subject).get(subj)
        created = False
        if s is None:
            self._L.warning("Requested subject not found: %s", subj)
            if create_if_missing:
                s, created = self.getOrCreate(subject.Subject, subject=subj, name=name)
                self._L.info("Created new subject: %s", subj)
        return s

    def subjects(self, subj=None, name=None):
        assert self._session is not None
        Q = self._session.query(models.subject.Subject)
        if name is not None:
            Q = Q.filter_by(name=name)
        if subj is not None:
            Q = Q.filter_by(subject=subj)
        return Q.order_by(models.subject.Subject.subject)

    def getPublicSubject(self):
        assert self._session is not None
        return self.getSubject(
            OPersist.PUBLIC_SUBJECT,
            name=OPersist.PUBLIC_SUBJECT_NAME,
            create_if_missing=True,
        )

    def getSubjectUsage(self, subj):
        res = {"accessrules": [], "things": []}
        the_subj = self.getSubject(subj)
        if the_subj is None:
            return res
        Q = self._session.query(models.accessrule.AccessRule)
        Q = Q.filter(models.accessrule.AccessRule.subjects.contains(the_subj))
        Q = Q.options(sqlalchemy.orm.load_only("_id"))
        for ar in Q:
            res["accessrules"].append(ar._id)
        Q = self._session.query(models.thing.Thing)
        Q = Q.filter(
            sqlalchemy.or_(
                models.thing.Thing.submitter == the_subj,
                models.thing.Thing.rights_holder == the_subj,
            )
        )
        Q = Q.options(sqlalchemy.orm.load_only("checksum_sha256"))
        for t in Q:
            res["things"].append(t.checksum_sha256)
        return res

    def setDefaultSubmitter(self, subject):
        """
        Sets the default submitter to the specified subject.

        Args:
            subject:

        Returns:

        """
        subj = subject
        if isinstance(subject, str):
            subj = self.getSubject(subject)
        self._default_submitter = subj
        conf = self.getConfig()
        conf["default_submitter"] = subject
        self.setConfig(conf)

    def getDefaultSubmitter(self):
        if self._default_submitter is not None:
            return self._default_submitter
        conf = self.getConfig()
        subj = conf.get("default_submitter")
        self._default_submitter = self.getSubject(subj)
        return self._default_submitter

    def setDefaultOwner(self, subject):
        subj = subject
        if isinstance(subject, str):
            subj = self.getSubject(subject)
        self._default_owner = subj
        conf = self.getConfig()
        conf["default_owner"] = subject
        self.setConfig(conf)

    def getDefaultOwner(self):
        if self._default_owner is not None:
            return self._default_owner
        conf = self.getConfig()
        subj = conf.get("default_owner")
        self._default_owner = self.getSubject(subj)
        return self._default_owner

    # ==================================
    # Access Rule operations
    def createAccessRule(self, permission, subjects):
        assert self._session is not None
        if len(subjects) < 1:
            raise ValueError("At least one subject is required for an access rule")
        ar = accessrule.AccessRule(permission=permission)
        ar.subjects = subjects
        self._session.add(ar)
        self.commit()
        self._L.info("Added access rule '%s'", ar)
        return ar

    def getPublicReadAccessRule(self):
        assert self._session is not None
        the_perm = models.accessrule.AllowedPermissions.fromString("read")
        the_subj = self.getPublicSubject()
        Q = self._session.query(models.accessrule.AccessRule)
        Q = Q.filter_by(permission=the_perm)
        Q = Q.filter(models.accessrule.AccessRule.subjects.contains(the_subj))
        # Get the oldest rule that matches
        Q = Q.order_by(models.accessrule.AccessRule.t.desc())
        the_ar = Q.first()
        if the_ar is not None:
            return the_ar
        the_ar = models.accessrule.AccessRule()
        the_ar.permission = the_perm
        the_ar.subjects.append(the_subj)
        self._session.add(the_ar)
        self.commit()
        self._L.info("Public read access rule added.")
        return the_ar

    def accessRules(self, perm: str = None, subj: str = None):
        Q = self._session.query(models.accessrule.AccessRule)
        if not perm is None:
            perm = models.accessrule.AllowedPermissions.fromString(perm)
            Q = Q.filter_by(permission=perm)
        if not subj is None:
            the_subj = self.getSubject(subj)
            Q = Q.filter(models.accessrule.AccessRule.subjects.contains(the_subj))
        return Q.order_by(models.accessrule.AccessRule._id)

    # ==================================
    # Thing operations

    def removeThing(self, sha256: str):
        assert self._session is not None
        self._ostore.remove(sha256)
        the_thing = self._session.query(models.thing.Thing).get(sha256)
        self._session.delete(the_thing)
        self._session.commit()
        self._L.info("Object %s removed.", sha256)

    def addThing(
        self,
        fname: str,
        identifier: str,
        hashes: dict = None,
        format_id: str = None,
        submitter: str = None,
        owner: str = None,
        access_rules: list = None,
        series_id: str = None,
        alt_identifiers: list = None,
        media_type: str = None,
        source: str = None,
        metadata: dict = None,
        obsoletes=None,
        date_uploaded=None,
    ):
        """
        Add a thing file to the store.

        The file is copied to the store. The file fname must exist and the identifier
        must be provided and must be unique in the store. Hashes are computed if not
        provided.

        Args:
            fname: Required. Path to the file to be added. Will be copied to the store and
                   named by sha256 hash
            identifier: Required. Identifier of the thing
            hashes: dict of {sha256, sha1, md5} values, computed if not provided
            format_id: The DataONE formatId of the thing
            submitter: Subject of the submitter
            owner: Subject of the owner, default to submitter
            access_rules: Access rules to be applied, public-read is default.
            series_id: Series identifier
            alt_identifiers: List of additional identifiers for this thing
            media_type: The mime type of the item
            source: origin of the content, e.g. full file path or absolute URL
            metadata: dictionary of additional stuff
            obsoletes: PID (identifier) of thing the new one will obsolete

        Returns:
            instance of thing
        """
        assert self._session is not None
        assert os.path.exists(fname)
        # Add to blob
        self._L.info("Persisting %s", identifier)
        self._L.info("Path = %s", fname)
        blob_metadata = metadata
        blob_metadata["file_name"] = os.path.basename(fname)
        blob_metadata["media_type"] = media_type
        blob_metadata["identifier"] = identifier
        if source is not None:
            blob_metadata["source"] = source
        if hashes is None:
            hashes = utils.computeChecksumsFile(
                fname,
                calc_md5=True,
                calc_sha1=True,
                calc_sha256=True,
            )
        fldr_dest, sha256, fn_dest = self._ostore.addFilePath(
            fname, hash=hashes["sha256"], metadata=blob_metadata
        )
        self._L.info("Adding database entry...")
        if source is None:
            source = os.path.abspath(fname)
        # Add to database
        try:
            # Check content state before creating
            # Ensure identifier is not used as a series id
            # assert count thing where series_id = value == 0
            if identifier is not None:
                match = (
                    self._session.query(models.thing.Thing)
                    .filter_by(series_id=identifier)
                    .one_or_none()
                )
                if match is not None:
                    raise ValueError(
                        f"Identifier '{identifier}' is used as a series_id"
                    )
            # Ensure series_id is not used as a pid
            # assert count thing where identifier = value == 0
            if series_id is not None:
                match = (
                    self._session.query(models.thing.Thing)
                    .filter_by(identifier=series_id)
                    .one_or_none()
                )
                if match is not None:
                    raise ValueError(
                        f"series_id '{series_id}' is used as an identifier"
                    )
            # get obsolete Thing if series_id is not None
            # if obsoletes doesn't match obsolete Thing then fail
            #
            if obsoletes is not None:
                # check obsoletes does not refer to a series_id
                match = (
                    self._session.query(models.thing.Thing)
                    .filter_by(series_id=obsoletes)
                    .one_or_none()
                )
                if match is not None:
                    raise ValueError(
                        f"Value of obsoletes must not be a series_id, {obsoletes}"
                    )
            else:
                if not series_id is None:
                    # look for matches
                    #
                    # series_id = "https://doi.org/10.5061/dryad.hm55b"
                    _things = self.getThingsSID(series_id)
                    _obsoleted = _things.first()
                    if _obsoleted is not None:
                        obsoletes = _obsoleted.identifier
                        _obsoleted.obsoleted_by = identifier

            if obsoletes is not None:
                # Get the thing being obsoleted
                match = (
                    self._session.query(models.thing.Thing)
                    .filter_by(identifier=obsoletes)
                    .one_or_none()
                )
                # verify that the series_id is not being changed
                if series_id is not None:
                    if match.series_id is not None:
                        assert match.series_id == series_id
                # Set here - will be comitted later or rolled back on error
                match.obsoleted_by = identifier
                match.date_modified = utils.dtnow()
                self._L.warning("OBSOLETED = %s", match)

            blob_fname = os.path.join(self._path_root, self._blob_path, fn_dest)
            the_thing = models.thing.Thing(checksum_sha256=sha256, content=fn_dest)
            the_thing.size_bytes = os.stat(blob_fname).st_size
            if submitter is None:
                submitter = self.getDefaultSubmitter()
            elif isinstance(submitter, str):
                submitter = self.getSubject(submitter)
            self._L.debug("Using submitter: %s", submitter)
            if owner is None:
                owner = self.getDefaultOwner()
            elif isinstance(owner, str):
                owner = self.getSubject(owner)
            if owner is None:
                owner = submitter
            self._L.debug("Using rights_holder: %s", owner)
            the_thing.checksum_md5 = hashes["md5"]
            the_thing.checksum_sha1 = hashes["sha1"]
            the_thing.source = source
            the_thing.file_name = blob_metadata["file_name"]
            the_thing.media_type_name = blob_metadata["media_type"]
            the_thing.identifier = blob_metadata["identifier"]
            the_thing.date_uploaded = date_uploaded
            the_thing.format_id = format_id
            the_thing.submitter = submitter
            the_thing.rights_holder = owner
            the_thing.series_id = series_id
            the_thing.identifiers = []
            the_thing.access_policy = []
            the_thing._meta = metadata
            the_thing.obsoletes = obsoletes
            if date_uploaded is None:
                the_thing.date_uploaded = utils.dtnow()
            if alt_identifiers is not None:
                self.identifiers = alt_identifiers
            if access_rules is None:
                the_thing.access_policy.append(self.getPublicReadAccessRule())
            else:
                the_thing.access_policy = access_rules
            self._L.debug(the_thing)
            self._session.add(the_thing)
            self.commit()
            return the_thing
        except sqlalchemy.exc.OperationalError as e:
            # this situation denotes a database read/write issue
            # such as "database is locked"
            # Return false to restart the session and try again
            self._L.error(e)
            self._L.error("Caught sqlalchemy.exc.OperationalError; attempting session restart...")
            status = self._ostore.remove(sha256)
            self._L.debug("Remove status = %s", status)
            return False
        except Exception as e:
            self._L.error("Failed to store entry in database.")
            self._L.error(e)
            status = self._ostore.remove(sha256)
            self._L.debug("Remove status = %s", status)
        return None

    def addThingBytes(
        self,
        obj: bytes,
        identifier: str,
        hashes: dict = None,
        format_id: str = None,
        submitter: str = None,
        owner: str = None,
        access_rules: list = None,
        series_id: str = None,
        alt_identifiers: list = None,
        media_type: str = None,
        source: str = None,
        metadata: dict = None,
        obsoletes=None,
        date_uploaded=None,
    ):
        """
        Adds the thing of bytes to the store.

        Ths implementation saves to a temporary file and delegates
        remaining operations to addThing.

        Args:
            obj:
            identifier:
            hashes:
            format_id:
            submitter:
            owner:
            access_rules:
            series_id:
            alt_identifiers:
            media_type:
            source:
            metadata:
            obsoletes:

        Returns:

        """
        ftmp = tempfile.NamedTemporaryFile(delete=False)
        ftmp_path = ftmp.name
        ftmp.write(obj)
        ftmp.close()
        try:
            thingAdd = self.addThing(
                ftmp_path,
                identifier=identifier,
                hashes=hashes,
                format_id=format_id,
                submitter=submitter,
                owner=owner,
                access_rules=access_rules,
                series_id=series_id,
                alt_identifiers=alt_identifiers,
                media_type=media_type,
                source=source,
                metadata=metadata,
                obsoletes=obsoletes,
                date_uploaded=date_uploaded,
            )
            if thingAdd == False:
                self._L.info("Entering session recovery loop")
                while True:
                    if self._session:
                        self._L.info("Closing old database connection session")
                        self.close()
                    self._L.info("Opening new database connection session")
                    self.open(allow_create=False)
                    self._L.info("Retrying persist with new session...")
                    thingAdd = self.addThing(
                        ftmp_path,
                        identifier=identifier,
                        hashes=hashes,
                        format_id=format_id,
                        submitter=submitter,
                        owner=owner,
                        access_rules=access_rules,
                        series_id=series_id,
                        alt_identifiers=alt_identifiers,
                        media_type=media_type,
                        source=source,
                        metadata=metadata,
                        obsoletes=obsoletes,
                        date_uploaded=date_uploaded,
                    )
                    if thingAdd:
                        self._L.info("Successfully stored under new session.")
                        break
                    elif thingAdd == None:
                        self._L.error(f"Could not store item under new session: {identifier}")
                        break
                    else:
                        self._L.error("Could not recover database session.")
                    if self._session:
                        self._L.info("Closing open database connection session.")
                        self.close()
                    self._L.info('Sleeping for 10 seconds.')
                    sleep(10)
                    self._L.info('Trying again...')
            return thingAdd
        finally:
            os.unlink(ftmp_path)

    def registerIdentifier(
        self,
        v,
        source,
        provider_id=None,
        provider_time=None,
        id_time=None,
        registrant=None,
        related=None,
    ):
        res = self._session.query(models.identifier.Identifier).filter_by(id=v).first()
        if res is not None:
            return False
        the_id = models.identifier.Identifier()
        the_id.id = v
        the_id.source = source
        the_id.provider_id = provider_id
        the_id.provider_time = provider_time
        the_id.id_time = id_time
        the_id.registrant = registrant
        the_id.related = related
        self._session.add(the_id)
        self.commit()

    def registerIdentifiers(self, the_thing):
        """
        Ensures that identifiers used by the_thing are recorded in the identifier table.

        Note that entries in the identifier table are not distinct by identifier value, so there
        may not be a direct association between an identifier entry and the_thing.

        If an identifier entry already exits, then it will not be touched. New identifier entries
        are made where the identifier does not exist in the database, in which case the source of the
        identifier will be set to "thing:<sha_256>:<field>" where sha_256 is the Thing sha_256 hash,
        and field is the field name of the identifier.

        Returns:
            int, the number of identifiers added to identifier table

        """
        assert self._session is not None
        nadded = 0
        if the_thing.identifier is not None:
            source = f"thing:{the_thing.checksum_sha256}:identifier"
            self.registerIdentifier(the_thing.identifier, source)
            nadded += 1
        if the_thing.series_id is not None:
            source = f"thing:{the_thing.checksum_sha256}:series_id"
            self.registerIdentifier(the_thing.series_id, source)
            nadded += 1
        for _id in the_thing.identifiers:
            source = f"thing:{_id}:identifiers"
            self.registerIdentifier(_id, source)
            nadded += 1
        return nadded

    def contentAbsPath(self, content_path):
        return os.path.abspath(os.path.join(self._blob_path, content_path))

    def getThingSha256(self, sha256):
        assert self._session is not None
        Q = self._session.query(models.thing.Thing)
        return Q.get(sha256)

    def getThingPID(self, identifier):
        assert self._session is not None
        Q = self._session.query(models.thing.Thing).filter_by(identifier=identifier)
        return Q.first()

    def getThingPIDorSID(self, identifier):
        # get by pid or most recent sid if not pid
        o = self.getThingPID(identifier)
        if o is None:
            Q = (
                self._session.query(models.thing.Thing)
                .filter_by(series_id=identifier)
                .order_by(models.thing.Thing.date_modified.desc())
            )
            o = Q.first()
        return o

    def getThingSha1(self, sha1):
        assert self._session is not None
        Q = self._session.query(models.thing.Thing).filter_by(checksum_sha1=sha1)
        return Q.first()

    def getThingMD5(self, md5):
        assert self._session is not None
        Q = self._session.query(models.thing.Thing).filter_by(checksum_md5=md5)
        return Q.first()

    def things(self):
        Q = self._session.query(models.thing.Thing)
        return Q.order_by(models.thing.Thing.t_added)

    def getThingsSID(self, series_id):
        Q = self._session.query(models.thing.Thing).filter_by(series_id=series_id)
        return Q.order_by(models.thing.Thing.date_modified.desc())

    def getThingsIdentifier(self, identifier):
        # TODO: match PID or SID or related identifiers, order by date_modified
        pass

    def countThings(self):
        Q = self._session.query(models.thing.Thing)
        return Q.count()

    def basicStatsThings(self):
        stats = {}
        Q = self._session.query(models.thing.Thing)
        stats["count"] = Q.count()
        newest = Q.order_by(models.thing.Thing.date_uploaded.desc()).limit(1).first()
        oldest = Q.order_by(models.thing.Thing.date_uploaded.asc()).limit(1).first()
        stats["newest"] = utils.datetimeToJsonStr(newest.date_uploaded)
        stats["oldest"] = utils.datetimeToJsonStr(oldest.date_uploaded)
        return stats
