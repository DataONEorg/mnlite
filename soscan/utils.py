import datetime

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
