import datetime
import dateparser

# raise Exception("don't use this")

JSON_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
"""datetime format string for generating JSON content
"""


def dtnow():
    """
    Now, with UTC timezone.

    Returns: datetime
    """
    return datetime.datetime.now(datetime.timezone.utc)


def datetimeToJsonStr(dt):
    """
    Render datetime to JSON datetime string

    Args:
        dt: datetime

    Returns: string
    """
    if dt is None:
        return None
    return dt.strftime(JSON_TIME_FORMAT)


def parseDatetimeString(ds):
    if ds is None:
        return None
    return dateparser.parse(ds, settings={"RETURN_AS_TIMEZONE_AWARE": True})
