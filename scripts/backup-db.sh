#!/bin/sh
# Dump the database to $BACKUP_DIR (default /backups) as <kind>-<UTC time>.dump (pg_dump custom format). Then delete
# every dump older than $MAX_AGE_DAYS (default 30), whatever its kind, and keep at most the newest $KEEP (default 14)
# of this kind. The age limit is what the privacy policy promises: purged data leaves the backups within 30 days.
# Runs in the postgres image (compose's backup services); connection details come from the PG* variables.
# Restore one with: pg_restore --clean --if-exists -d winter_dragon /backups/<file>.dump
# Tests: bash scripts/test-backup-db.sh
set -eu

kind="$1"
dir="${BACKUP_DIR:-/backups}"
keep="${KEEP:-14}"
max_age_days="${MAX_AGE_DAYS:-30}"
file="$dir/$kind-$(date -u +%Y%m%dT%H%M%SZ).dump"

pg_dump --format=custom --file="$file"
echo "Backed up to $file"
find "$dir" -maxdepth 1 -name '*.dump' -mmin +"$((max_age_days * 24 * 60))" -exec rm -- {} +
ls -1t "$dir/$kind"-*.dump | tail -n +"$((keep + 1))" | xargs -r rm --
