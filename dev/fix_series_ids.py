"""
Supervised normalization of the ``thing`` table in a mnlite sqlite3 database.

Rules:
1. If ``identifiers`` (JSON list of strings) contains a value starting with
   ``doi:10.82144/``, copy the first such value into ``series_id``.
2. For each row with a ``doi:10.82144/`` identifier, follow ``obsoletes`` (matched
   against the ``identifier`` column) and set the obsoleted row's ``series_id``
   to that row's ``series_id``; repeat along the whole version chain, stopping
   at a row that itself has a ``doi:10.82144/`` identifier (it owns its own chain).
3. Otherwise, if a row has no such DOI, was not reached by a version chain, and
   its ``series_id`` starts with ``https``, set ``archived`` = 1.
4. ``date_modified`` is set to the current time on every changed row.

Runs as a dry run unless ``--apply`` is given. Each change is reported and,
with --apply, confirmed interactively unless ``--yes`` is given.
"""
import argparse
import datetime
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
    counts = {"series_id": 0, "archived": 0, "chain_series_id": 0, "skipped": 0}

    def approve(msg: str) -> bool:
        print(msg)
        if not prompt:
            return True
        return input("  apply? [y/N] ").strip().lower() in ("y", "yes")

    def set_series(pk, old, new, label):
        if old == new:
            return False
        if not approve(f"[{pk[:12]}] {label}: {old!r} -> {new!r}"):
            counts["skipped"] += 1
            return False
        if args.apply:
            cur.execute(
                f"UPDATE {t} SET series_id=?, date_modified=? WHERE checksum_sha256=?",
                (new, ts, pk),
            )
        return True

    rows = cur.execute(
        f"SELECT checksum_sha256, identifier, series_id, identifiers, obsoletes, archived FROM {t}"
    ).fetchall()

    try:
        # Pass 1: DOI rows take their series_id from the DOI
        doi_rows = []  # (checksum, series_id, obsoletes)
        non_doi = []
        for row in rows:
            pk = row["checksum_sha256"]
            dois = [i for i in parse_identifiers(row["identifiers"]) if i.startswith(DOI_PREFIX)]
            if dois:
                if set_series(pk, row["series_id"], dois[0], "series_id"):
                    counts["series_id"] += 1
                doi_rows.append((pk, dois[0], row["obsoletes"]))
            else:
                non_doi.append(row)

        # Pass 2: walk each version chain from the DOI row. Rows reached here
        # receive the chain's series_id, so they must not be archived below.
        chained = set()
        for pk, series, old_id in doi_rows:
            visited = {pk}
            while old_id:
                old = cur.execute(
                    f"SELECT checksum_sha256, identifier, series_id, identifiers, obsoletes FROM {t} WHERE identifier=?",
                    (old_id,),
                ).fetchone()
                if old is None:
                    print(f"[{pk[:12]}] WARNING obsoletes {old_id!r} not found; chain ends")
                    break
                opk = old["checksum_sha256"]
                if opk in visited:
                    print(f"[{pk[:12]}] WARNING cycle at {old_id!r}; chain ends")
                    break
                visited.add(opk)
                if any(i.startswith(DOI_PREFIX) for i in parse_identifiers(old["identifiers"])):
                    break  # that row owns its own series and chain
                chained.add(opk)
                if set_series(opk, old["series_id"], series, "chain series_id"):
                    counts["chain_series_id"] += 1
                old_id = old["obsoletes"]

        # Pass 3: archive remaining non-DOI rows that still have an https series_id
        for row in non_doi:
            pk = row["checksum_sha256"]
            sid = row["series_id"]
            if pk in chained or not (sid and sid.startswith("https")) or row["archived"]:
                continue
            if approve(f"[{pk[:12]}] archived: {row['archived']!r} -> 1 (series_id {sid!r})"):
                if args.apply:
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
