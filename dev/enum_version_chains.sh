#!/usr/bin/env bash
# Count version chains in the `thing` table using obsoletes / obsoleted_by.
#
# Usage: count_version_chains.sh [-t TABLE] [-l LOGFILE] DATABASE
#   -t  table name (default: thing)
#   -l  write details of problem chains to LOGFILE (default: stderr)
#
# Definitions
#   chain     a connected set of rows linked through obsoletes / obsoleted_by
#             (either direction), where at least one row has a link set.
#             Rows with neither field set are counted separately as standalone.
#   head      a row whose obsoleted_by is empty (the newest version).
#   archived  a chain is "archived" when every head is archived (all rows if it
#             has no head); otherwise "not archived".
#   dangling  obsoletes / obsoleted_by naming an identifier absent from the table.
#   Also logged: non-reciprocal links, chains with no head (cycle) or several heads.
set -euo pipefail

table=thing
log=
while getopts "t:l:" opt; do
  case $opt in
    t) table=$OPTARG ;;
    l) log=$OPTARG ;;
    *) echo "Usage: $0 [-t TABLE] [-l LOGFILE] DATABASE" >&2; exit 2 ;;
  esac
done
shift $((OPTIND - 1))
[[ $# -eq 1 ]] || { echo "Usage: $0 [-t TABLE] [-l LOGFILE] DATABASE" >&2; exit 2; }
db=$1
[[ -f $db ]] || { echo "Database not found: $db" >&2; exit 1; }
command -v sqlite3 >/dev/null || { echo "sqlite3 not found" >&2; exit 1; }
[[ $table =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || { echo "Invalid table name: $table" >&2; exit 1; }

out=${log:-/dev/stderr}
if [[ -n $log ]]; then : > "$log"; fi

# Read-only; all work happens in temp tables.
sql_setup=$(cat <<SQL
.timeout 30000
CREATE TEMP TABLE r AS
  SELECT checksum_sha256 AS pk, identifier AS id,
         NULLIF(obsoletes, '') AS obs, NULLIF(obsoleted_by, '') AS obsby,
         COALESCE(archived, 0) AS arch
  FROM $table;
CREATE INDEX temp.r_id ON r(id);
CREATE INDEX temp.r_pk ON r(pk);

-- undirected link graph between existing rows
CREATE TEMP TABLE e AS
  SELECT a.pk AS x, b.pk AS y FROM r a JOIN r b ON b.id = a.obs
  UNION SELECT b.pk, a.pk FROM r a JOIN r b ON b.id = a.obs
  UNION SELECT a.pk, b.pk FROM r a JOIN r b ON b.id = a.obsby
  UNION SELECT b.pk, a.pk FROM r a JOIN r b ON b.id = a.obsby;
CREATE INDEX temp.e_x ON e(x);

-- connected components, labelled by the smallest pk
CREATE TEMP TABLE c AS
  WITH RECURSIVE reach(src, dst) AS (
    SELECT pk, pk FROM r
    UNION
    SELECT reach.src, e.y FROM reach JOIN e ON e.x = reach.dst)
  SELECT src AS pk, MIN(dst) AS comp FROM reach GROUP BY src;
CREATE INDEX temp.c_pk ON c(pk);

CREATE TEMP TABLE chain AS
  SELECT c.comp,
         COUNT(*) AS n,
         MAX(r.obs IS NOT NULL OR r.obsby IS NOT NULL) AS linked,
         SUM(r.obsby IS NULL) AS heads,
         SUM(r.obsby IS NULL AND r.arch = 0) AS heads_unarch,
         SUM(r.arch = 0) AS rows_unarch
  FROM c JOIN r ON r.pk = c.pk GROUP BY c.comp;
UPDATE chain SET linked = 1 WHERE linked IS NULL;

-- problems, one row each
CREATE TEMP TABLE prob AS
  SELECT c.comp, r.id, 'dangling obsoletes -> ' || r.obs AS what
    FROM r JOIN c ON c.pk = r.pk
   WHERE r.obs IS NOT NULL AND r.obs NOT IN (SELECT id FROM r WHERE id IS NOT NULL)
  UNION ALL
  SELECT c.comp, r.id, 'dangling obsoleted_by -> ' || r.obsby
    FROM r JOIN c ON c.pk = r.pk
   WHERE r.obsby IS NOT NULL AND r.obsby NOT IN (SELECT id FROM r WHERE id IS NOT NULL)
  UNION ALL
  SELECT c.comp, a.id, 'non-reciprocal: obsoletes ' || b.id || ' but its obsoleted_by is ' || COALESCE(b.obsby, 'NULL')
    FROM r a JOIN r b ON b.id = a.obs JOIN c ON c.pk = a.pk
   WHERE b.obsby IS NOT a.id
  UNION ALL
  SELECT c.comp, a.id, 'non-reciprocal: obsoleted_by ' || b.id || ' but its obsoletes is ' || COALESCE(b.obs, 'NULL')
    FROM r a JOIN r b ON b.id = a.obsby JOIN c ON c.pk = a.pk
   WHERE b.obs IS NOT a.id;
SQL
)

# chain.class: 1 = archived
sql_class="CREATE TEMP TABLE cls AS SELECT comp, n, heads,
  CASE WHEN (heads > 0 AND heads_unarch = 0) OR (heads = 0 AND rows_unarch = 0)
       THEN 'archived' ELSE 'not archived' END AS state
  FROM chain WHERE linked = 1;"

sql_report=$(cat <<'SQL'
SELECT 'total rows:            ' || COUNT(*) FROM r;
SELECT 'standalone (no links): ' || COUNT(*) FROM chain WHERE linked = 0;
SELECT 'version chains:        ' || COUNT(*) FROM cls;
SELECT '  archived:            ' || COUNT(*) FROM cls WHERE state = 'archived';
SELECT '  not archived:        ' || COUNT(*) FROM cls WHERE state = 'not archived';
SELECT 'longest chain:         ' || COALESCE(MAX(n), 0) FROM cls;
SELECT 'chains with dangling links:  ' || COUNT(DISTINCT comp) FROM prob WHERE what LIKE 'dangling%';
SELECT '  archived:                  ' || COUNT(DISTINCT p.comp) FROM prob p JOIN cls USING (comp) WHERE p.what LIKE 'dangling%' AND cls.state = 'archived';
SELECT '  not archived:              ' || COUNT(DISTINCT p.comp) FROM prob p JOIN cls USING (comp) WHERE p.what LIKE 'dangling%' AND cls.state = 'not archived';
SELECT 'chains with non-reciprocal links: ' || COUNT(DISTINCT comp) FROM prob WHERE what LIKE 'non-reciprocal%';
SELECT 'chains with no head (cycle):      ' || COUNT(*) FROM cls WHERE heads = 0;
SELECT 'chains with several heads:        ' || COUNT(*) FROM cls WHERE heads > 1;
SQL
)

sql_log=$(cat <<'SQL'
.separator " | "
SELECT 'PROBLEM chain=' || substr(cls.comp, 1, 16) || ' state=' || cls.state || ' rows=' || cls.n || ' heads=' || cls.heads || ' :: ' || COALESCE(p.id, '?') || ' :: ' || p.what
  FROM prob p JOIN cls USING (comp) ORDER BY cls.comp, p.id;
SELECT 'PROBLEM chain=' || substr(comp, 1, 16) || ' state=' || state || ' rows=' || n || ' :: no head (cycle)' FROM cls WHERE heads = 0
UNION ALL
SELECT 'PROBLEM chain=' || substr(comp, 1, 16) || ' state=' || state || ' rows=' || n || ' :: ' || heads || ' heads' FROM cls WHERE heads > 1;
SQL
)

# One sqlite3 session: temp tables are session-local. Summary -> stdout,
# problem details -> log. Dot-command .output switches between them.
sqlite3 -readonly "$db" <<SQL
$sql_setup
$sql_class
$sql_report
.output $out
$sql_log
.output stdout
SQL
if [[ -n $log ]]; then
  echo "problem log: $log ($(wc -l < "$log") lines)"
fi
