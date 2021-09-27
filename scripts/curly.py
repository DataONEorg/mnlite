"""
HTTP REquest introspection
"""
import sys
import logging
import click
import requests
import pyld

try:
    import orjson as json
except ModuleNotFoundError:
    import json

import opersist.rdfutils

# import igsn_lib.link_requests

LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "WARN": logging.WARNING,
    "ERROR": logging.ERROR,
    "FATAL": logging.CRITICAL,
    "CRITICAL": logging.CRITICAL,
}
LOG_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"
LOG_FORMAT = "%(asctime)s %(name)s:%(levelname)s: %(message)s"
TIMEOUT = 10.0  # seconds
# https://tools.ietf.org/html/rfc7231#section-5.5.3
USER_AGENT = "curly/0.1;python/3.9"  # "curl/7.64.1" #


def loadJsonLD(response, normalize=True):
    jsonld = pyld.jsonld.load_html(
        response.content,
        response.url,
        profile=None,
        options={"extractAllScripts": True},
    )
    if normalize:
        return opersist.rdfutils.normalizeSONamespace(jsonld, base=response.url)
    return jsonld


def getJsonLDChecksum(jsonld):
    pass


def printResponseInfo(r, show_response=False, show_json=False, f=sys.stderr):
    l = []
    l += f"{r.url}\n"
    l += f"        status: {r.status_code}\n"
    l += f"          date: {r.headers.get('Date', '-')}\n"
    l += f" last-modified: {r.headers.get('Last-Modified', '-')}\n"
    l += f"  content-type: {r.headers.get('Content-Type', '-')}\n"
    l += f"          link: {r.headers.get('Link', '-')}\n"
    l += f"       elapsed: {r.elapsed}\n"
    f.writelines(l)
    if show_response:
        print(r.text)
    if show_json:
        jld = loadJsonLD(r)
        print(json.dumps(jld, indent=2))


def printResponse(response, show_response=False, show_json=False, f=sys.stderr):
    L = logging.getLogger("printResponse")
    L.debug(response.request.headers)

    i = 0
    l = []
    for r in response.history:
        f.write(f"Response {i}\n")
        printResponseInfo(r, f=f)
        i += 1
    f.write(f"Response {i}\n")
    printResponseInfo(response, show_response=show_response, show_json=show_json, f=f)


def printResponsePath(response):
    i = 0
    status_code = ""
    content_type = ""
    for r in response.history:
        print(f"{i:02}:{status_code:>4} {content_type} {r.url}")
        status_code = r.status_code
        content_type = f"Content-Type: {r.headers.get('Content-Type', '-')}"
        i += 1
    r = response
    print(f"{i:02}:{status_code:>4} {content_type} {r.url}")
    status_code = r.status_code
    content_type = f"Content-Type: {r.headers.get('Content-Type', '-')}"
    i += 1
    print(f"{i:02}:{status_code:>4} {content_type}")


@click.group()
@click.option(
    "-V",
    "--verbosity",
    default="INFO",
    help="Specify logging level",
    show_default=True,
)
@click.pass_context
def main(ctx, verbosity):
    ctx.ensure_object(dict)
    verbosity = verbosity.upper()
    logging.basicConfig(
        level=LOG_LEVELS.get(verbosity, logging.INFO),
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
    )
    L = logging.getLogger("main")
    if verbosity not in LOG_LEVELS.keys():
        L.warning("%s is not a log level, set to INFO", verbosity)
    # ctx.obj["folder"] = os.path.abspath(folder)


@main.command("jsonld")
@click.argument("url")
@click.option("-a", "--accept", default="*/*", help="Value for request Accept header")
@click.option(
    "-o",
    "--original",
    default=False,
    show_default=True,
    is_flag=True,
    help="Show JSON-LD as extracted with no transformation.",
)
@click.option(
    "-c",
    "--checksum",
    default=False,
    show_default=True,
    is_flag=True,
    help="Compute SHA256 checksum.",
)
@click.option(
    "-i",
    "--identifiers",
    default=False,
    show_default=True,
    is_flag=True,
    help="Extract identifiers.",
)
@click.pass_context
def getJsonLD(ctx, url, accept, original, checksum, identifiers):
    L = logging.getLogger("jsonld")
    # session = igsn_lib.link_requests.LinkSession()
    session = requests.Session()
    # accept = "application/ld+json"
    headers = {
        "Accept": accept,
        "User-Agent": USER_AGENT,
    }
    response = session.get(url, headers=headers, allow_redirects=True, timeout=TIMEOUT)
    for h in response.history:
        L.info(f"{h.status_code} {h.url}")
    L.info(f"{response.status_code} {response.url}")
    jsonld = loadJsonLD(response, normalize=not original)
    print(json.dumps(jsonld, indent=2))
    if checksum:
        checksums = opersist.rdfutils.computeJSONLDChecksums(jsonld)
        for k, v in checksums.items():
            print(f"{k}:{v}")
    if identifiers:
        ids = opersist.rdfutils.extractIdentifiers(jsonld)
        for g in ids:
            print(f"@id: {g['@id']}")
            print(f"  url: {g['url']}")
            for i in g["identifier"]:
                print(f"  identifier: {i}")


@main.command("hops")
@click.argument("url")
@click.option("-a", "--accept", default="*/*", help="Value for request Accept header")
@click.option(
    "-b",
    "--show-body",
    default=False,
    show_default=True,
    is_flag=True,
    help="Show response body.",
)
@click.option(
    "--path-only",
    default=False,
    show_default=True,
    is_flag=True,
    help="Show path to resolution only",
)
@click.pass_context
def doResolve(ctx, url, accept, show_body, path_only):
    L = logging.getLogger("hops")
    # session = igsn_lib.link_requests.LinkSession()
    session = requests.Session()
    headers = {
        "Accept": accept,
        "User-Agent": USER_AGENT,
    }
    response = session.get(url, headers=headers, allow_redirects=True, timeout=TIMEOUT)
    if path_only:
        printResponsePath(response)
    else:
        printResponse(response, show_response=show_body, show_json=False)


if __name__ == "__main__":
    main()
