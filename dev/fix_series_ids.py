"""
Supervised normalization of the ``thing`` table in a mnlite sqlite3 database.

Target series_id per row:
1. A row whose ``identifiers`` (JSON list of strings) contains a value starting
   with ``doi:10.82144/`` gets the first such value as its series_id.
2. Following ``obsoletes`` (matched against the ``identifier`` column) from each
   such row, every older row in the version chain gets that same series_id. A
   walk stops at a row that itself has a ``doi:10.82144/`` identifier.
3. A row with no such DOI, not reached by a version chain, and a series_id
   starting with ``https`` has ``archived`` set to 1.

The MN API does not allow a series_id to be changed once set, so:
- a row with no series_id has it set in place;
- a row with a different series_id is left untouched except for obsoleted_by,
  and a replacement row is inserted: a copy with series_id set to the target,
  ``identifier`` and ``checksum_sha256`` suffixed with ``-<8 hex of sha256 of
  the new series_id>`` (the content/hash otherwise unchanged), ``obsoletes`` =
  the old identifier and ``obsoleted_by`` = whatever the old row was obsoleted
  by. The old row's ``obsoleted_by`` is set to the new identifier and the
  newer row's ``obsoletes`` is re-pointed at the replacement, so the replacement
  sits in the version chain directly after the row it replaces.
  Access rules are copied. Re-running is a no-op.

``date_modified`` is set to the current time on every changed or new row.

Runs as a dry run unless ``--apply`` is given. Each change is reported and,
with --apply, confirmed interactively unless ``--yes`` is given.
"""
import argparse
import datetime
import hashlib
import json
import shutil
import sqlite3
import sys

DOI_PREFIX = "doi:10.82144/"


def now_str() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")


def parse_identifiers(raw):
    if raw is None:
        return []
    try:
        val = json.loads(raw) if isinstance(raw, (str, bytes)) else raw
    except json.JSONDecodeError:
        return []
    if isinstance(val, str):
        return [val]
    if isinstance(val, list):
        return [v for v in val if isinstance(v, str)]
    return []


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("database", help="path to sqlite3 database")
    ap.add_argument("--table", default="thing")
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    ap.add_argument("--yes", action="store_true", help="do not prompt for each change")
    ap.add_argument("--no-backup", action="store_true", help="skip copying the db before applying")
    args = ap.parse_args()

    if args.apply and not args.no_backup:
        backup = f"{args.database}.bak-{datetime.datetime.now():%Y%m%d%H%M%S}"
        shutil.copy2(args.database, backup)
        print(f"Backup written to {backup}")

    t = args.table
    con = sqlite3.connect(args.database)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    ts = now_str()
    prompt = args.apply and not args.yes
    counts = {"series_id": 0, "replaced": 0, "archived": 0, "skipped": 0}
    has_acl = cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='thing_accessrule'"
    ).fetchone() is not None

    def approve(msg: str) -> bool:
        print(msg)
        if not prompt:
            return True
        return input("  apply? [y/N] ").strip().lower() in ("y", "yes")

    def get_by_pk(pk):
        return cur.execute(f"SELECT * FROM {t} WHERE checksum_sha256=?", (pk,)).fetchone()

    def get_by_id(ident):
        return cur.execute(f"SELECT * FROM {t} WHERE identifier=?", (ident,)).fetchone()

    def replace_row(old, target):
        suffix = "-" + hashlib.sha256(target.encode()).hexdigest()[:8]
        new_pk = old["checksum_sha256"] + suffix
        new_id = old["identifier"] + suffix
        existing = get_by_id(new_id)
        if existing is not None and existing["series_id"] == target:
            return  # already replaced by an earlier run
        if existing is not None or get_by_pk(new_pk):
            print(f"[{old['checksum_sha256'][:12]}] WARNING {new_id!r} already exists; skipped")
            counts["skipped"] += 1
            return
        if not approve(
            f"[{old['checksum_sha256'][:12]}] series_id {old['series_id']!r} -> {target!r}: "
            f"new row {new_id!r} obsoletes {old['identifier']!r}"
        ):
            counts["skipped"] += 1
            return
        new = dict(old)
        new.update(
            checksum_sha256=new_pk,
            identifier=new_id,
            series_id=target,
            obsoletes=old["identifier"],
            obsoleted_by=old["obsoleted_by"],
            date_modified=ts,
        )
        cols = list(new)
        cur.execute(
            f"INSERT INTO {t} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
            [new[c] for c in cols],
        )
        if has_acl:
            cur.execute(
                "INSERT INTO thing_accessrule (thing_id, accessrule_id) "
                "SELECT ?, accessrule_id FROM thing_accessrule WHERE thing_id=?",
                (new_pk, old["checksum_sha256"]),
            )
        cur.execute(
            f"UPDATE {t} SET obsoleted_by=?, date_modified=? WHERE checksum_sha256=?",
            (new_id, ts, old["checksum_sha256"]),
        )
        if old["obsoleted_by"]:
            cur.execute(
                f"UPDATE {t} SET obsoletes=?, date_modified=? WHERE identifier=?",
                (new_id, ts, old["obsoleted_by"]),
            )
        counts["replaced"] += 1

    def has_doi(row):
        return any(i.startswith(DOI_PREFIX) for i in parse_identifiers(row["identifiers"]))

    try:
        # Plan (read-only): target series_id per row
        rows = cur.execute(f"SELECT * FROM {t}").fetchall()
        targets = {}  # pk -> target series_id
        chained = set()
        doi_rows = []
        for row in rows:
            dois = [i for i in parse_identifiers(row["identifiers"]) if i.startswith(DOI_PREFIX)]
            if dois:
                targets[row["checksum_sha256"]] = dois[0]
                doi_rows.append((row, dois[0]))
        for row, series in doi_rows:
            pk = row["checksum_sha256"]
            visited = {pk}
            old_id = row["obsoletes"]
            while old_id:
                old = get_by_id(old_id)
                if old is None:
                    print(f"[{pk[:12]}] WARNING obsoletes {old_id!r} not found; chain ends")
                    break
                opk = old["checksum_sha256"]
                if opk in visited:
                    print(f"[{pk[:12]}] WARNING cycle at {old_id!r}; chain ends")
                    break
                visited.add(opk)
                if has_doi(old):
                    break  # that row owns its own series and chain
                chained.add(opk)
                if targets.setdefault(opk, series) != series:
                    print(f"[{opk[:12]}] WARNING reached from two series; keeping {targets[opk]!r}")
                old_id = old["obsoletes"]

        # Apply
        for pk, target in targets.items():
            row = get_by_pk(pk)
            cur_sid = row["series_id"]
            if cur_sid == target:
                continue
            if not row["identifier"]:
                print(f"[{pk[:12]}] WARNING no identifier; cannot set series_id")
                continue
            if not cur_sid:
                if approve(f"[{pk[:12]}] series_id: {cur_sid!r} -> {target!r}"):
                    cur.execute(
                        f"UPDATE {t} SET series_id=?, date_modified=? WHERE checksum_sha256=?",
                        (target, ts, pk),
                    )
                    counts["series_id"] += 1
                else:
                    counts["skipped"] += 1
                continue
            replace_row(row, target)

        # Archive remaining non-DOI rows that still have an https series_id
        for row in rows:
            pk = row["checksum_sha256"]
            if pk in targets:
                continue
            sid = row["series_id"]
            if not (sid and sid.startswith("https")) or row["archived"]:
                continue
            if approve(f"[{pk[:12]}] archived: {row['archived']!r} -> 1 (series_id {sid!r})"):
                cur.execute(
                    f"UPDATE {t} SET archived=1, date_modified=? WHERE checksum_sha256=?",
                    (ts, pk),
                )
                counts["archived"] += 1
            else:
                counts["skipped"] += 1
    except (EOFError, KeyboardInterrupt):
        print("\nAborted; rolling back.")
        con.rollback()
        return 1

    if args.apply:
        con.commit()
    else:
        con.rollback()
    print(("Applied" if args.apply else "Dry run") + f": {counts}")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
