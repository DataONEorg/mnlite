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
    "doi:10.82144/B2": "-3864cdcf",
    "doi:10.82144/C1": "-72ef361a",
    "doi:10.82144/D1": "-8eb1aafe",
    "doi:10.82144/F1a": "-ea5894e7",
    "doi:10.82144/K1": "-b6f252df",
    SEAMAP: "-94d11b2e",
}

# Original rows after the run: pk -> (series_id, archived, modified)
OLD = {
    "a1": ("old", 0, True),  # obsoleted_by set
    "a2": ("https://a2", 0, True),
    "a3": ("doi:10.82144/AAA", 0, True),  # NULL series_id: set in place
    "a4": ("plain", 0, True),
    "b1": ("b1s", 0, True),
    "b2": ("b2s", 0, True),
    "b3": ("b3s", 0, True),
    "c1": ("c1s", 0, True),
    "d1": ("d1s", 0, True),
    "d2": ("d2s", 0, True),
    "e1": ("doi:10.82144/E1", 0, False),
    "f1": ("f1s", 0, True),
    "g1": ("https://g1", 1, True),
    "h1": ("https://h1", 1, False),
    "i1": ("urn:uuid:1", 0, False),
    "j1": ("https://j1", 1, True),
    "j2": ("j2s", 0, False),
    "k1": ("https://k1", 0, True),
    H1: ("https://seamap.env.duke.edu/dataset/2050", 0, True),
    H2: ("https://seamap.env.duke.edu/dataset/2050", 0, True),
    H3: ("https://seamap.env.duke.edu/dataset/2050", 0, True),
}
# replaced old pk -> target series_id
REPLACED = {
    "a1": "doi:10.82144/AAA", "a2": "doi:10.82144/AAA", "a4": "doi:10.82144/AAA",
    "b1": "doi:10.82144/B1", "b2": "doi:10.82144/B2", "b3": "doi:10.82144/B2",
    "c1": "doi:10.82144/C1", "d1": "doi:10.82144/D1", "d2": "doi:10.82144/D1",
    "f1": "doi:10.82144/F1a", "k1": "doi:10.82144/K1",
    H1: SEAMAP, H2: SEAMAP, H3: SEAMAP,
}
IDENT = {pk: "sha256:" + pk if len(pk) == 64 else pk.upper() for pk in OLD}


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
    acl = con.execute("SELECT thing_id FROM thing_accessrule").fetchall()
    con.close()
    return rows, [a[0] for a in acl]


def new_pk(old):
    return old + SFX[REPLACED[old]]


def test_apply_yes(db):
    r = run(db, "--apply", "--yes", "--no-backup")
    assert r.returncode == 0, r.stderr
    rows, acl = load(db)
    assert "MISSING" in r.stdout and "cycle" in r.stdout

    # Old rows keep their series_id (SID can't change once set); only the
    # NULL-series row a3 is changed in place.
    for pk, (sid, arch, mod) in OLD.items():
        row = rows[pk]
        assert (row["series_id"], row["archived"], row["date_modified"] is not None) == (sid, arch, mod), pk

    # Exactly one new row per replaced row, nothing else
    assert set(rows) == set(OLD) | {new_pk(o) for o in REPLACED}
    for old, target in REPLACED.items():
        n, o = rows[new_pk(old)], rows[old]
        assert n["series_id"] == target
        assert n["identifier"] == o["identifier"] + SFX[target]
        assert n["obsoletes"] == o["identifier"]
        assert n["date_modified"] is not None
        assert n["identifiers"] == o["identifiers"] and n["archived"] == 0
        # access rules are copied
        assert acl.count(new_pk(old)) == acl.count(old) == 1

    # Reciprocal links for every row whose partner exists
    by_id = {r["identifier"]: r for r in rows.values()}
    for row in rows.values():
        if row["obsoletes"] in by_id:
            assert by_id[row["obsoletes"]]["obsoleted_by"] == row["identifier"], row["identifier"]
        if row["obsoleted_by"] in by_id:
            assert by_id[row["obsoleted_by"]]["obsoletes"] == row["identifier"], row["identifier"]


def chain(rows, head):
    """Identifiers from head following obsoletes."""
    by_id = {r["identifier"]: r for r in rows.values()}
    out, cur = [], head
    while cur in by_id and cur not in out:
        out.append(cur)
        cur = by_id[cur]["obsoletes"]
    return out


def test_chain_a_order(db):
    run(db, "--apply", "--yes", "--no-backup")
    rows, _ = load(db)
    s = "-9bb3eeb1"
    assert rows[new_pk("a1")]["obsoleted_by"] is None  # new head
    assert chain(rows, "A1" + s) == ["A1" + s, "A1", "A2" + s, "A2", "A3", "A4" + s, "A4"]
    sids = [rows[p]["series_id"] for p in ("a1-9bb3eeb1", "a2-9bb3eeb1", "a3", "a4-9bb3eeb1")]
    assert sids == ["doi:10.82144/AAA"] * 4


def test_seamap_chain(db):
    run(db, "--apply", "--yes", "--no-backup")
    rows, _ = load(db)
    s = SFX[SEAMAP]
    i = lambda h: "sha256:" + h
    assert chain(rows, i(H3) + s) == [
        i(H3) + s, i(H3), i(H2) + s, i(H2), i(H1) + s, i(H1)
    ]
    # the content hash is preserved as a prefix of the new PK
    assert new_pk(H3).startswith(H3)


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
