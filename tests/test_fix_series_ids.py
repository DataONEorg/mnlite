import pathlib
import sqlite3
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "dev" / "fix_series_ids.py"
FIXTURE = ROOT / "tests" / "fixtures" / "series_ids.sql"

# pk: (series_id, archived, modified)
EXPECTED = {
    "a1": ("doi:10.82144/AAA", 0, True),
    "a2": ("doi:10.82144/AAA", 0, True),  # chained rows are not archived,
    "a3": ("doi:10.82144/AAA", 0, True),
    "a4": ("doi:10.82144/AAA", 0, True),
    "b1": ("doi:10.82144/B1", 0, True),
    "b2": ("doi:10.82144/B2", 0, True),
    "b3": ("doi:10.82144/B2", 0, True),
    "c1": ("doi:10.82144/C1", 0, True),
    "d1": ("doi:10.82144/D1", 0, True),
    "d2": ("doi:10.82144/D1", 0, True),
    "e1": ("doi:10.82144/E1", 0, False),
    "f1": ("doi:10.82144/F1a", 0, True),
    "g1": ("https://g1", 1, True),
    "h1": ("https://h1", 1, False),
    "i1": ("urn:uuid:1", 0, False),
    "j1": ("https://j1", 1, True),
    "j2": ("j2s", 0, False),
    "k1": ("doi:10.82144/K1", 0, True),
    "ce02cd1d06a2c27527d5eda970d105e6a8b7a3f8be80ca813ae4ed4e9fb355eb": ("doi:10.82144/422375df", 0, True),
    "6c142b471b13faf094d7ddec8255413f41ebe53ec8117dc9166e0c10e96f56d1": ("doi:10.82144/422375df", 0, True),
    "02fd78dddb6ad9b28c0a3b9d3cc344a13ec06331e8e3dc984b401208bbe7f2a0": ("doi:10.82144/422375df", 0, True),
}


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


def test_apply_yes(db):
    r = run(db, "--apply", "--yes", "--no-backup")
    assert r.returncode == 0, r.stderr
    got = {pk: (sid, arch, dm is not None) for pk, sid, arch, dm in snapshot(db)}
    assert got == EXPECTED
    assert "MISSING" in r.stdout and "cycle" in r.stdout


def test_idempotent(db):
    run(db, "--apply", "--yes", "--no-backup")
    first = snapshot(db)
    r = run(db, "--apply", "--yes", "--no-backup")
    assert "'series_id': 0, 'archived': 0, 'chain_series_id': 0" in r.stdout
    assert snapshot(db) == first


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
