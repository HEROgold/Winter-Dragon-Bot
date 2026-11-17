#!/usr/bin/env bash
# Tests for backup-db.sh. Each case runs the script against a scratch backup dir
# with a fake `pg_dump` on PATH that writes an empty dump.
#   bash scripts/test-backup-db.sh
# check() evals its condition later, so the conditions stay single-quoted (SC2016).
# shellcheck disable=SC2016
set -uo pipefail

script="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/backup-db.sh"

failures=0
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

mkdir -p "$work/bin"
cat >"$work/bin/pg_dump" <<'EOF'
#!/usr/bin/env bash
for arg in "$@"; do
  case "$arg" in --file=*) touch "${arg#--file=}" ;; esac
done
EOF
chmod +x "$work/bin/pg_dump"

# new_dir makes a fresh backup dir for one case.
new_dir() {
  dir="$work/backups-$1"
  mkdir -p "$dir"
}

# dump makes a dump of <kind> that is <days> days old.
dump() {
  local file="$dir/$1-$2d.dump"
  touch -d "@$(($(date +%s) - $2 * 86400))" "$file"
}

run() {
  PATH="$work/bin:$PATH" BACKUP_DIR="$dir" KEEP="${KEEP:-14}" sh "$script" "$1" >/dev/null
}

count() {
  find "$dir" -name "$1-*.dump" | wc -l | tr -d ' '
}

check() {
  if eval "$2"; then
    echo "ok   $1"
  else
    echo "FAIL $1"
    failures=$((failures + 1))
  fi
}

new_dir age
dump pre-migrate 31
dump pre-migrate 5
dump daily 45
run pre-migrate
check "deletes a dump older than 30 days though fewer than KEEP exist" '[[ ! -e "$dir/pre-migrate-31d.dump" ]]'
check "deletes old dumps of other kinds too" '[[ ! -e "$dir/daily-45d.dump" ]]'
check "keeps a dump younger than 30 days" '[[ -e "$dir/pre-migrate-5d.dump" ]]'
check "writes the new dump" '[[ "$(find "$dir" -name "pre-migrate-*Z.dump" | wc -l | tr -d " ")" == 1 ]]'

new_dir count
for days in 1 2 3 4; do dump pre-migrate "$days"; done
dump daily 2
KEEP=3 run pre-migrate
check "keeps only the newest KEEP of the kind" '[[ "$(count pre-migrate)" == 3 ]]'
check "deletes the oldest of the kind first" '[[ ! -e "$dir/pre-migrate-3d.dump" && ! -e "$dir/pre-migrate-4d.dump" ]]'
check "leaves other kinds under the count limit alone" '[[ -e "$dir/daily-2d.dump" ]]'

new_dir max-age
dump pre-migrate 8
dump pre-migrate 6
MAX_AGE_DAYS=7 run pre-migrate
check "MAX_AGE_DAYS sets the age limit" '[[ ! -e "$dir/pre-migrate-8d.dump" && -e "$dir/pre-migrate-6d.dump" ]]'

if ((failures)); then
  echo "$failures failed"
  exit 1
fi
echo "all passed"
