import os
import re
import uuid
import datetime
import dateparser
import cgi
import contextlib

try:
    import orjson as json
except ModuleNotFoundError:
    import json

import hashlib

# For splitting HTTP header values
HEADER_VALUE_SPLIT = re.compile('(?:["<].*?[">]|[^,])+')

# block size when reading files for hashing
BLOCK_SIZE = 65536

# datetime format string for generating JSON content
JSON_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S%z"

# Indent this much when computing hash on JSON
# None means no space and no new lines
JSON_HASH_INDENT = None

# Match a space
RE_SPACE = re.compile("\s")


def stringHasSpace(s):
    return RE_SPACE.search(s)


@contextlib.contextmanager
def pushd(new_dir):
    """
    with pushd(new_dir):
      do stuff
    """
    previous_dir = os.getcwd()
    os.chdir(new_dir)
    try:
        yield
    finally:
        os.chdir(previous_dir)


def bytesChecksums(b, sha256=True, sha1=True, md5=True):
    """
    Computes hashes for the provided Bytes
    Args:
        b: bytes

    Returns:
        hashes
    """
    hashes = {"sha256": None, "sha1": None, "md5": None}
    if sha256:
        hashes["sha256"] = hashlib.sha256(b).hexdigest()
    if sha1:
        hashes["sha1"] = hashlib.sha1(b).hexdigest()
    if md5:
        hashes["md5"] = hashlib.md5(b).hexdigest()
    return hashes, b


def stringChecksums(s, encoding="UTF-8", sha256=True, sha1=True, md5=True):
    b = s.encode(encoding)
    return bytesChecksums(b, sha256=sha256, sha1=sha1, md5=md5)


def jsonChecksums(doc):
    """
    Compute checksums for a JSON object.

    The JSON is serialized to UTF-8 text with no indenting, no space between items
    and key-value, and sorted keys.

    Args:
        doc: The JSON structure

    Returns:
        dict of hashes, bytes

    """
    b = json.dumps(
        doc, separators=(",", ":"), sort_keys=True, indent=JSON_HASH_INDENT
    ).encode("UTF-8")
    return bytesChecksums(b)


def floChecksums(flo, sha256=True, sha1=True, md5=True):
    """
    Computes hashes for object in file stream.

    Args:
        flo: file like object open for reading

    Returns:
        dict of md5, sha1, sha256 hashes.

    """
    hashes = {"sha256": None, "sha1": None, "md5": None}
    hsha256 = None
    hsha1 = None
    hmd5 = None
    if sha256:
        hsha256 = hashlib.sha256()
    if sha1:
        hsha1 = hashlib.sha1()
    if md5:
        hmd5 = hashlib.md5()
    fbuf = flo.read(HASH_BLOCK_SIZE)
    while len(fbuf) > 0:
        if sha256:
            hsha256.update(fbuf)
        if sha1:
            hsha1.update(fbuf)
        if md5:
            hmd5.update(fbuf)
        fbuf = flo.read(HASH_BLOCK_SIZE)
    if sha256:
        hashes["sha256"] = hsha256.hexdigest()
    if sha1:
        hashes["sha1"] = hsha1.hexdigest()
    if md5:
        hashes["md5"] = md5.hexdigest()
    return hashes


def fileChecksums(fname, sha256=True, sha1=True, md5=True):
    """
    Compute checksums for a file on disk
    """
    with open(fname, "rb") as flo:
        return floChecksums(flo, sha256=sha256, sha1=sha1, md5=md5)


def generateUUID():
    return str(uuid.uuid4())


def datetimeToJsonStr(dt):
    if dt is None:
        return None
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        # Naive timestamp, convention is this must be UTC
        return f"{dt.strftime(JSON_TIME_FORMAT)}Z"
    return dt.strftime(JSON_TIME_FORMAT)


def dtnow():
    """
    Get datetime for now in UTC timezone.

    Returns:
        datetime.datetime with UTC timezone

    Example:

        .. jupyter-execute::

           import igsn_lib.time
           print(igsn_lib.time.dtnow())
    """
    return datetime.datetime.now(datetime.timezone.utc)


def utcFromDateTime(dt, assume_local=True):
    # is dt timezone aware?
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        if assume_local:
            # convert local time to tz aware utc
            dt.astimezone(datetime.timezone.utc)
        else:
            # asume dt is in UTC, add timezone
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt
    # convert to utc timezone
    return dt.astimezone(datetime.timezone.utc)


def datetimeFromSomething(V, assume_local=True):
    if V is None:
        return None
    if isinstance(V, datetime.datetime):
        return utcFromDateTime(V, assume_local=assume_local)
    if isinstance(V, float) or isinstance(V, int):
        return utcFromDateTime(
            datetime.datetime.fromtimestamp(V), assume_local=assume_local
        )
    if isinstance(V, str):
        return utcFromDateTime(
            dateparser.parse(V, settings={"RETURN_AS_TIMEZONE_AWARE": True}),
            assume_local=assume_local,
        )
    return None


# Note: rel may contain multiple values: https://tools.ietf.org/html/rfc8288#section-3.3
def _uriValue(v):
    v = v.strip()
    if v[0] != "<" and v[-1] != ">":
        return v
    return v[1:-1]


def parseHTTPHeader(hv):
    """
    Parse a potentially multi-valued header

    Given::
      'form-data; name="fieldName"; filename="filename.jpg"'

    Response::
      [('form-data', {'filename': 'filename.jpg', 'name': 'fieldName'})]

    Args:
        hv: header value

    Returns: list of [v, dict]

    """
    res = []
    # split by comma, but not within <> or ""
    vals = re.findall(HEADER_VALUE_SPLIT, hv)
    for val in vals:
        parts = cgi.parse_header((val))
        res.append((_uriValue(parts[0]), parts[1]))
    return res
