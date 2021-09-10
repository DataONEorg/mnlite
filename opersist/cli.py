"""
Provides command line utility for interacting with an opersist instance.
"""

import os
import logging
import click

try:
    import orjson as json
except ModuleNotFoundError:
    import json

import opersist
import opersist.models

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


def getOpersistInstance(folder, db_url=None):
    op = opersist.OPersist(folder, db_url=db_url)
    op.open()
    return op


@click.group()
@click.option(
    "-V",
    "--verbosity",
    default="INFO",
    help="Specify logging level",
    show_default=True,
)
@click.option(
    "-f", "--folder", default=opersist.DEFAULT_STORE, help="Folder for opersist content"
)
@click.pass_context
def main(ctx, verbosity, folder):
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
    ctx.obj["folder"] = os.path.abspath(folder)


@main.command("init")
@click.pass_context
def initializeInstance(ctx):
    '''
    Initialize a new instance; -f path/to/instance
    '''
    L = logging.getLogger("init")
    folder = ctx.obj["folder"]
    L.info("Setting up opersist in %s", folder)
    op = getOpersistInstance(folder)
    print(json.dumps(op.getConfig(), indent="  "))
    op.close()


@main.command("sub")
@click.pass_context
@click.option("-n", "--name", default=None, help="Name of subject")
@click.option("-s", "--subj", default=None, help="Subject value of subject")
@click.option(
    "-o",
    "--operation",
    type=click.Choice(
        [
            "list",
            "c",
            "create",
            "u",
            "update",
            "d",
            "delete",
        ],
        case_sensitive=False,
    ),
    default="list",
    help="Operation to perform",
)
def subjects(ctx, name, subj, operation):
    '''
    Manage subjects in the opersist instance.
    '''
    L = logging.getLogger("subjects")
    folder = ctx.obj["folder"]
    op = getOpersistInstance(folder)
    if operation in ["c", "create"]:
        new_subject = op.getSubject(subj, name=name, create_if_missing=True)
        print(new_subject)
        return
    if operation in ["d", "delete"]:
        usage = op.getSubjectUsage(subj)
        print(usage)
        # TODO: delete subject if not used
        raise NotImplementedError("delete subject")
        return
    print("[", end="")
    dlm = None
    for subject in op.subjects(subj=subj, name=name):
        if not dlm is None:
            print(
                dlm,
            )
        print(subject, end="")
        dlm = ","
    print("]")


@main.command("ar")
@click.pass_context
@click.option("-p", "--perm", default=None, help="Permission (R, W, or C)")
@click.option("-s", "--subj", multiple=True, default=[], help="Subject value")
@click.option("-i", "--id", "ar_id", default=None, help="Subject value")
@click.option(
    "-o",
    "--operation",
    type=click.Choice(
        [
            "list",
            "c",
            "create",
            "u",
            "update",
            "d",
            "delete",
            "a",
            "add",
            "r",
            "remove",
        ],
        case_sensitive=False,
    ),
    default="list",
    help="Operation to perform",
)
def accessRules(ctx, perm, subj, ar_id, operation):
    '''
    Manage access rules for the opersist instance
    '''
    L = logging.getLogger("accessRules")
    folder = ctx.obj["folder"]
    op = getOpersistInstance(folder)

    # create a new access rule
    if operation in ["c", "create"]:
        if perm is None:
            raise ValueError("Permission is required when creating an access rule")
        if len(subj) < 1:
            raise ValueError(
                "At least one subject is required to create an access rule"
            )
        subjects = []
        for s in subj:
            subjects.append(op.getSubject(s))
        new_ar = op.createAccessRule(perm, subjects)
        print(new_ar)
        return

    # Add a subject to an access rule
    if operation in ["a", "add"]:
        if ar_id is None:
            raise ValueError("Access rule ID is required to add a subject")
        if len(subj) < 1:
            raise ValueError(
                "At least one subject is required to add a subject to an access rule"
            )
        the_ar = op._session.query(opersist.models.accessrule.AccessRule).get(ar_id)
        for s in subj:
            the_subj = op.getSubject(s)
            if not the_subj is None:
                the_ar.subjects.append(the_subj)
        op._session.commit()
        print(the_ar)
        return
    # List access rules
    if len(subj) > 1:
        L.warning("Only filtering access rules on first provided subject: %s", subj)
    if len(subj) > 0:
        subj = subj[0]
    else:
        subj = None
    for arule in op.accessRules(perm=perm, subj=subj):
        print(arule)


@main.command("thing")
@click.pass_context
@click.option(
    "-o",
    "--operation",
    type=click.Choice(
        [
            "list",
            "c",
            "create",
            "u",
            "update",
            "d",
            "delete",
            "purge",
        ],
        case_sensitive=False,
    ),
    default="list",
    help="Operation to perform",
)
@click.option("-f", "--fname", help="Path to file to add")
@click.option("--sha256", default=None, help="SHA256 value identifying a thing")
@click.option(
    "-i",
    "--identifier",
    default=None,
    help="PID for object, unique in store, defaults to file name",
)
@click.option(
    "-t", "--format_id", default="application/octet-stream", help="FormatId of object"
)
@click.option("--sid", "series_id", default=None, help="SID for object")
def things(ctx, operation, fname, sha256, identifier, format_id, series_id):
    '''
    Manage things in the opersist instance.
    '''
    L = logging.getLogger("things")
    folder = ctx.obj["folder"]
    op = getOpersistInstance(folder)

    if operation in ["d", "delete"]:
        if sha256 is None:
            L.error("SHA256 hash value is required to remove an entry")
            return
        op.removeThing(sha256)
        return

    if operation == "purge":
        # Remove all the things
        c = 0
        for t in op.things():
            L.warning("DELETING: %s", t.identifier)
            op.removeThing(t.checksum_sha256)
            c += 1
        L.warning("Deleted %s things.", c)
        return

    if operation in ["c", "create"]:
        if not os.path.exists(fname):
            raise ValueError(f"The specified file does not exist: {fname}")
        if identifier is None:
            identifier = os.path.basename(fname)
            L.warning("Identifier not provided, using filename %s", identifier)
        the_thing = op.addThing(
            fname, identifier=identifier, format_id=format_id, series_id=series_id
        )

        print(the_thing)
        return

    for athing in op.things():
        print(athing)


@main.command("rel")
@click.pass_context
def relations(ctx):
    pass


if __name__ == "__main__":
    main()
