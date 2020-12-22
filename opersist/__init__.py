import os
import logging
import ojson as json
import sqlalchemy.exc
import sqlalchemy.orm.exc
from . import utils
from . import flob
from . import models
from .models import request
from .models import identifier
from .models import relation
from .models import subject
from .models import accessrule
from .models import thing


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
            conf_dest.write(json.dumps(conf, indent="  "))

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
                self._ostore = flob.FLOB(conf["data_folder"])
            #Ensure the public subject is available
            subj = self.getPublicReadAccessRule()
        else:
            conf = self.getConfig()
            with utils.pushd(self._path_root):
                if self._session is None:
                    self._session = models.getSession(self._engine)
                if self._ostore is None:
                    self._ostore = flob.FLOB(conf["data_folder"])

    def getSession(self):
        assert self._session is not None
        return self._session

    def removeSession(self):
        pass
        #self.close()
        #print("Remove Session")
        #if not self._session is None:
        #    self._session.remove()

    def close(self):
        if not self._session is None:
            self._session.remove()
            #self._session.close()
            self._session = None
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
                self._session.flush()
                self._session.commit()
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
        self._session.flush()
        self._session.commit()
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
        self._session.commit()
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
        identifier: str = None,
        format_id: str = None,
        submitter: str = None,
        owner: str = None,
        access_rules: list = None,
        series_id: str = None,
        alt_identifiers: list = None,
        media_type: str = None,
    ):
        """
        Add a thing to the store.

        Args:
            fname: Path to the file to be added. Will be copied to the store and named by sha256 hash
            identifier: Identifier of the thing
            format_id: The DataONE formatId of the thing
            submitter: Subject of the submitter
            owner: Subject of the owner, default to submitter
            access_rules: Access rules to be applied, public-read is default.
            series_id: Series identifier
            alt_identifiers: List of additional identifiers for this thing

        Returns:
            instance of thing
        """
        assert self._session is not None
        assert os.path.exists(fname)
        # Add to blob
        blob_metadata = {
            "file_name": os.path.basename(fname),
            "media_type": media_type,
            "identifier": identifier,
        }
        hashes = utils.computeFileHashes(
            fname,
            calc_md5=True,
            calc_sha1=True,
            calc_sha256=True,
        )
        fldr_dest, sha256, fn_dest = self._ostore.addFilePath(
            fname, hash=hashes["sha256"], metadata=blob_metadata
        )
        # Add to database
        try:
            blob_fname = os.path.join(self._path_root, self._blob_path, fn_dest)
            the_thing = models.thing.Thing(checksum_sha256=sha256, content=fn_dest)
            the_thing.size_bytes = os.stat(blob_fname).st_size
            if submitter is None:
                submitter = self.getDefaultSubmitter()
            elif isinstance(submitter, str):
                submitter = self.getSubject(submitter)
            self._L.info("Using submitter: %s", submitter)
            if owner is None:
                owner = self.getDefaultOwner()
            elif isinstance(owner, str):
                owner = self.getSubject(owner)
            if owner is None:
                owner = submitter
            self._L.info("Using rights_holder: %s", owner)
            the_thing.checksum_md5 = hashes["md5"]
            the_thing.checksum_sha1 = hashes["sha1"]
            the_thing.file_name = blob_metadata["file_name"]
            the_thing.media_type = blob_metadata["media_type"]
            the_thing.identifier = blob_metadata["identifier"]
            the_thing.format_id = format_id
            the_thing.submitter = submitter
            the_thing.rights_holder = owner
            the_thing.series_id = series_id
            the_thing.identifiers = []
            the_thing.access_policy = []
            if alt_identifiers is not None:
                self.identifiers = alt_identifiers
            if access_rules is None:
                the_thing.access_policy.append(self.getPublicReadAccessRule())
            else:
                the_thing.access_policy = access_rules
            self._L.info(the_thing)
            self._session.add(the_thing)
            self._session.commit()
            return the_thing
        except Exception as e:
            self._L.error("Failed to store entry in database.")
            self._L.error(e)
            status = self._ostore.remove(sha256)
            self._L.debug("Remove status = %s", status)
        return None

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
                .filter_by(identifier=identifier)
                .order_by(models.thing.Thing.date_modified.desc())
            )
            o = Q.first()
        return o

    def getThingSha1(self, sha1):
        pass

    def getThingMD5(self, md5):
        pass

    def things(self):
        Q = self._session.query(models.thing.Thing)
        return Q.order_by(models.thing.Thing.t_added)

    def getThingsSID(self, series_id):
        pass

    def getThingsIdentifier(self, identifier):
        pass
