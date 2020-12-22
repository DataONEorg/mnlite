import ojson as json
import datetime
import requests
import sqlalchemy
import sqlalchemy.dialects.postgresql
import opersist.utils
import opersist.models

REQUEST_NONE = -9999


class Request(opersist.models.Base):

    __tablename__ = "request"

    id = sqlalchemy.Column(
        sqlalchemy.dialects.postgresql.UUID,
        default=opersist.utils.generateUUID,
        primary_key=True,
        doc="Generated UUID",
    )
    t = sqlalchemy.Column(
        sqlalchemy.DateTime(timezone=True),
        default=opersist.utils.dtnow,
        doc="When request was initiated, UTC",
    )
    dt = sqlalchemy.Column(
        sqlalchemy.Integer, default=0, doc="Time taken (sec) to complete request"
    )
    url_start = sqlalchemy.Column(sqlalchemy.String, doc="Starting request url")
    url_end = sqlalchemy.Column(sqlalchemy.String, doc="Final request url")
    nhops = sqlalchemy.Column(
        sqlalchemy.Integer, default=0, doc="Number of redirects to final retrieval"
    )
    status = sqlalchemy.Column(
        sqlalchemy.Integer, default=REQUEST_NONE, doc="Status of completed request"
    )
    req_format = sqlalchemy.Column(
        sqlalchemy.String, nullable=True, default=None, doc="Requested media type"
    )
    media_type = sqlalchemy.Column(
        sqlalchemy.String,
        nullable=True,
        default=None,
        doc="Reported media type in response",
    )
    # e.g. Content-Disposition: inline; filename="myfile.txt"
    filename = sqlalchemy.Column(
        sqlalchemy.String,
        nullable=True,
        default=None,
        doc="Reported filename in response Content-Dispositon header, if any",
    )
    t_mod = sqlalchemy.Column(
        sqlalchemy.DateTime(timezone=True),
        nullable=True,
        default=None,
        doc="HTTP time reported in Last-Modified header if available",
    )

    def asJsonDict(self):
        res = {
            "id": self.id,
            "t": opersist.utils.datetimeToJsonStr(self.t),
            "dt": self.dt,
            "url_start": self.url_start,
            "url_end": self.url_end,
            "nhops": self.nhops,
            "status": self.status,
            "req_format": self.req_format,
            "media_type": self.media_type,
            "filename": self.filename,
            "t_mod": opersist.utils.datetimeToJsonStr(self.t_mod),
        }
        return res

    def __repr__(self):
        return json.dumps(self.asJsonDict(), indent="  ")

    def fromResponse(
        self, response: requests.Response, tstart: datetime.datetime = None
    ):
        """
        Populate record from a requests.Response object

        Args:
            response: The Response object from a requests HTTP request
            tstart: Starting time, otherwise retrieved from Date header of first response

        Returns:
            Nothing
        """
        if tstart is None:
            if len(response.history) > 0:
                tstart = opersist.utils.datetimeFromSomething(
                    response.history[0].headers.get("Date", None)
                )
            else:
                tstart = opersist.utils.datetimeFromSomething(
                    response.headers.get("Date", None)
                )
        else:
            tstart = opersist.utils.utcFromDateTime(tstart)
        self.t = tstart
        self.dt = response.elapsed.total_seconds()
        for h in response.history:
            self.dt = self.dt + h.elapsed.total_seconds()
        self.nhops = len(response.history)
        if self.nhops > 0:
            self.url_start = response.history[0].url
        else:
            self.url_start = response.url
        self.url_end = response.url
        self.status = response.status_code
        self.req_format = response.request.headers.get("Accept", None)
        ctype = response.headers.get("Content", None)
        if not ctype is None:
            self.media_type = ctype.split(";")[0].strip()
        fname = response.headers.get("Content-Disposition", None)
        if not fname is None:
            parts = opersist.utils.parseHTTPHeader(fname)
            try:
                self.filename = parts[0][1].get("filename", None)
            except KeyError as e:
                pass
        last_mod = response.headers.get("Last-Modified", None)
        if not last_mod is None:
            self.t_mod = opersist.utils.datetimeFromSomething(last_mod)
