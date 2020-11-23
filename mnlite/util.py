
import datetime
import dateparser

JSON_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
"""datetime format string for generating JSON content
"""

def datetimeToJsonStr(dt):
    if dt is None:
        return None
    return dt.strftime(JSON_TIME_FORMAT)

def datetimeFromSomething(V):
    if V is None:
        return None
    if isinstance(V, datetime.datetime):
        return V
    if isinstance(V, float) or isinstance(V, int):
        # asumes this is a timestamp
        return datetime.datetime.fromtimestamp(V, tz=datetime.timezone.utc)
    if isinstance(V, str):
        return dateparser.parse(
            V, settings={"TIMEZONE": "+0000", "RETURN_AS_TIMEZONE_AWARE": True}
        )
    return None
