import os
import re
import uuid
import datetime
import dateparser
import cgi
import contextlib
import hashlib

HEADER_VALUE_SPLIT = re.compile('(?:["<].*?[">]|[^,])+')

BLOCK_SIZE = 65536

JSON_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
"""datetime format string for generating JSON content
"""

RE_SPACE = re.compile('\s')

def stringHasSpace(s):
    return RE_SPACE.search(s)


@contextlib.contextmanager
def pushd(new_dir):
    '''
    with pushd(new_dir):
      do stuff
    '''
    previous_dir = os.getcwd()
    os.chdir(new_dir)
    try:
        yield
    finally:
        os.chdir(previous_dir)


def computeFileHashes(fname, calc_md5=False, calc_sha1=False, calc_sha256=False):
    hashers = {
        "md5": hashlib.md5() if calc_md5 else None,
        "sha1": hashlib.sha1() if calc_sha1 else None,
        "sha256": hashlib.sha256() if calc_sha256 else None,
    }
    with open(fname, "rb") as fsrc:
        fbuf = fsrc.read(BLOCK_SIZE)
        while len(fbuf) > 0:
            for k,h in hashers.items():
                if h is not None:
                    h.update(fbuf)
            fbuf = fsrc.read(BLOCK_SIZE)
    res = {}
    for k,v in hashers.items():
        res[k] = None
        if v is not None:
            res[k] = v.hexdigest()
    return res


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
