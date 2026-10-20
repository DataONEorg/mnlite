#!/usr/bin/env bash
# Set date_modified to the current UTC time on every row in the `thing` table
# whose `identifier` matches a line of a text file (one identifier per line).
#
# Usage: touch_date_modified.sh [-n] [-t TABLE] DATABASE IDENTIFIERS_FILE
#   -n  dry run: list matching rows and report unmatched lines, change nothing
#   -t  table name (default: thing)
set -euo pipefail

table=thing
dry=0
while getopts "nt:" opt; do
  case $opt in
    n) dry=1 ;;
    t) table=$OPTARG ;;
    *) echo "Usage: $0 [-n] [-t TABLE] DATABASE IDENTIFIERS_FILE" >&2; exit 2 ;;
  esac
done
shift $((OPTIND - 1))
[[ $# -eq 2 ]] || { echo "Usage: $0 [-n] [-t TABLE] DATABASE IDENTIFIERS_FILE" >&2; exit 2; }
db=$1
list=$2

[[ -f $db ]] || { echo "Database not found: $db" >&2; exit 1; }
[[ -r $list ]] || { echo "Cannot read: $list" >&2; exit 1; }
command -v sqlite3 >/dev/null || { echo "sqlite3 not found" >&2; exit 1; }
[[ $table =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || { echo "Invalid table name: $table" >&2; exit 1; }

# Same layout as SQLAlchemy / the other dev scripts: YYYY-MM-DD HH:MM:SS.ffffff (UTC)
now="strftime('%Y-%m-%d %H:%M:%f','now') || '000'"

# Strip CRs and blank lines; double single quotes for SQL literals.
inserts=$(tr -d '\r' < "$list" | sed -e '/^[[:space:]]*$/d' -e "s/'/''/g" -e "s/.*/INSERT OR IGNORE INTO ids VALUES ('&');/")
if [[ -z $inserts ]]; then
  echo "No identifiers in $list" >&2
  exit 1
fi

if (( dry )); then
  action="SELECT 'WOULD UPDATE: ' || identifier FROM $table WHERE identifier IN (SELECT id FROM ids);"
else
  action="UPDATE $table SET date_modified = $now WHERE identifier IN (SELECT id FROM ids);"
fi

sqlite3 "$db" <<SQL
.bail on
.timeout 30000
CREATE TEMP TABLE ids (id TEXT PRIMARY KEY);
BEGIN;
$inserts
$action
SELECT 'matched: ' || count(*) FROM $table WHERE identifier IN (SELECT id FROM ids);
SELECT 'not found: ' || id FROM ids WHERE id NOT IN (SELECT identifier FROM $table WHERE identifier IS NOT NULL);
$( ((dry)) && echo ROLLBACK\; || echo COMMIT\; )
SQL
