#!/bin/sh
# Dump the database to /backups as <kind>-<UTC time>.dump (pg_dump custom format) and keep the newest $KEEP of that
# kind. Runs in the postgres image (compose's backup services); connection details come from the PG* variables.
# Restore one with: pg_restore --clean --if-exists -d winter_dragon /backups/<file>.dump
set -eu

kind="$1"
keep="${KEEP:-14}"
file="/backups/$kind-$(date -u +%Y%m%dT%H%M%SZ).dump"

pg_dump --format=custom --file="$file"
echo "Backed up to $file"
ls -1t /backups/"$kind"-*.dump | tail -n +"$((keep + 1))" | xargs -r rm --
