import pathlib
import sqlite3
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "dev" / "fix_series_ids.py"
FIXTURE = ROOT / "tests" / "fixtures" / "series_ids.sql"

H1 = "ce02cd1d06a2c27527d5eda970d105e6a8b7a3f8be80ca813ae4ed4e9fb355eb"
H2 = "6c142b471b13faf094d7ddec8255413f41ebe53ec8117dc9166e0c10e96f56d1"
H3 = "02fd78dddb6ad9b28c0a3b9d3cc344a13ec06331e8e3dc984b401208bbe7f2a0"
SEAMAP = "doi:10.82144/422375df"
SFX = {  # suffix = "-" + first 8 hex of sha256(target series_id)
    "doi:10.82144/AAA": "-9bb3eeb1",
    "doi:10.82144/B1": "-642fd8f6",
    "doi:10.82144/C1": "-72ef361a",
    "doi:10.82144/F1a": "-ea5894e7",
    "doi:10.82144/K1": "-b6f252df",
    SEAMAP: "-94d11b2e",
}

# Untouched rows: obsoleted ones (never modified), and heads needing no change
UNTOUCHED = {
    "a2": "https://a2", "a3": None, "a4": "plain",
    "b2": "b2s", "b3": "b3s",
    "d1": "d1s", "d2": "d2s",  # cycle: every row is obsoleted
    "e1": "doi:10.82144/E1", "h1": "https://h1", "i1": "urn:uuid:1", "j2": "j2s",
    H1: "https://seamap.env.duke.edu/dataset/2050",
    H2: "https://seamap.env.duke.edu/dataset/2050",
}
# Heads whose series_id is replaced: old pk -> target series_id
REPLACED = {
    "a1": "doi:10.82144/AAA", "b1": "doi:10.82144/B1", "c1": "doi:10.82144/C1",
    "f1": "doi:10.82144/F1a", "k1": "doi:10.82144/K1", H3: SEAMAP,
}
# Heads without a DOI and with an https series_id get archived
ARCHIVED = {"g1", "j1"}


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "t.db"
    con = sqlite3.connect(path)
    con.executescript(FIXTURE.read_text())
    con.commit()
    con.close()
    return path


def run(db, *args, stdin=""):
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(db), *args],
        input=stdin, capture_output=True, text=True,
    )


def snapshot(db):
    con = sqlite3.connect(db)
    rows = con.execute(
        "SELECT checksum_sha256, series_id, archived, date_modified FROM thing"
    ).fetchall()
    con.close()
    return rows


def test_dry_run_changes_nothing(db):
    before = snapshot(db)
    r = run(db)
    assert r.returncode == 0 and "Dry run" in r.stdout
    assert snapshot(db) == before


def load(db):
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    rows = {r["checksum_sha256"]: dict(r) for r in con.execute("SELECT * FROM thing")}
    acl = [a[0] for a in con.execute("SELECT thing_id FROM thing_accessrule")]
    con.close()
    return rows, acl


def new_pk(old):
    return old + SFX[REPLACED[old]]


def test_apply_yes(db):
    before, _ = load(db)
    r = run(db, "--apply", "--yes", "--no-backup")
    assert r.returncode == 0, r.stderr
    rows, acl = load(db)

    # Untouched rows are byte-for-byte unchanged, including date_modified
    for pk in UNTOUCHED:
        assert rows[pk] == before[pk], pk

    # Replaced heads keep their series_id; only obsoleted_by/date_modified change
    for old, target in REPLACED.items():
        o, n = rows[old], rows[new_pk(old)]
        assert o["series_id"] == before[old]["series_id"]
        assert o["obsoleted_by"] == n["identifier"]
        assert o["date_modified"] is not None
        assert {k: v for k, v in o.items() if k not in ("obsoleted_by", "date_modified")} == \
               {k: v for k, v in before[old].items() if k not in ("obsoleted_by", "date_modified")}
        # replacement is the new head
        assert n["series_id"] == target
        assert n["identifier"] == o["identifier"] + SFX[target]
        assert n["obsoletes"] == o["identifier"] and n["obsoleted_by"] is None
        assert n["identifiers"] == o["identifiers"] and n["archived"] == 0
        assert n["date_modified"] is not None
        assert acl.count(new_pk(old)) == acl.count(old) == 1

    # Archived heads
    for pk in ARCHIVED:
        assert rows[pk]["archived"] == 1 and rows[pk]["date_modified"] is not None

    # No other rows added or changed
    assert set(rows) == set(before) | {new_pk(o) for o in REPLACED}
    changed = {pk for pk in before if rows[pk] != before[pk]}
    assert changed == set(REPLACED) | ARCHIVED


def test_seamap_chain(db):
    run(db, "--apply", "--yes", "--no-backup")
    rows, _ = load(db)
    i = lambda h: "sha256:" + h
    new = i(H3) + SFX[SEAMAP]
    assert rows[H3 + SFX[SEAMAP]]["identifier"] == new  # hash preserved as PK prefix
    by_id = {r["identifier"]: r for r in rows.values()}
    order, cur = [], new
    while cur in by_id:
        order.append(cur)
        cur = by_id[cur]["obsoletes"]
    assert order == [new, i(H3), i(H2), i(H1)]


def test_idempotent(db):
    run(db, "--apply", "--yes", "--no-backup")
    first = load(db)
    r = run(db, "--apply", "--yes", "--no-backup")
    assert "'series_id': 0, 'replaced': 0, 'archived': 0" in r.stdout
    assert load(db) == first


def test_backup_written(db):
    run(db, "--apply", "--yes")
    assert list(db.parent.glob("t.db.bak-*"))


def test_interactive_decline(db):
    before = snapshot(db)
    r = run(db, "--apply", "--no-backup", stdin="n\n" * 100)
    assert r.returncode == 0
    assert snapshot(db) == before
    assert "'skipped':" in r.stdout


def test_interactive_abort_rolls_back(db):
    before = snapshot(db)
    r = run(db, "--apply", "--no-backup", stdin="y\ny\n")  # EOF after two answers
    assert r.returncode == 1
    assert snapshot(db) == before
