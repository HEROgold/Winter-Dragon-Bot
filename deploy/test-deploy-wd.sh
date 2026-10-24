#!/usr/bin/env bash
# Tests for deploy-wd.sh. Each case runs the script in a scratch project dir
# with a fake `docker` on PATH that records its arguments.
#   bash deploy/test-deploy-wd.sh
# check() evals its condition later, so the conditions stay single-quoted
# (SC2016), and `status` is read only inside them (SC2034).
# shellcheck disable=SC2016,SC2034
set -uo pipefail

script="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/deploy-wd.sh"
image_a="ghcr.io/herogold/winter-dragon-bot@sha256:$(printf 'a%.0s' {1..64})"
image_b="ghcr.io/herogold/winter-dragon-bot@sha256:$(printf 'b%.0s' {1..64})"
compose_args="compose -f compose.yml --env-file .env --env-file .env.deploy"
# What .env.deploy holds after deploying each image as v1.2.3.
env_a=$(printf 'WD_IMAGE=%s\nWD_VERSION=v1.2.3' "$image_a")
env_b=$(printf 'WD_IMAGE=%s\nWD_VERSION=v1.2.3' "$image_b")

failures=0
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

mkdir -p "$work/bin"
cat >"$work/bin/docker" <<'EOF'
#!/usr/bin/env bash
echo "$*" >>"$FAKE_DOCKER_LOG"
# FAKE_UP_FAILS=n fails `compose ... up` while it is at most the n-th up in this log.
if [[ "$1" == compose && " $* " == *" up "* ]]; then
  count=$(( $(cat "$FAKE_DOCKER_LOG.up" 2>/dev/null || echo 0) + 1 ))
  echo "$count" >"$FAKE_DOCKER_LOG.up"
  (( count <= ${FAKE_UP_FAILS:-0} )) && exit 1
fi
exit 0
EOF
chmod +x "$work/bin/docker"

# new_project makes a fresh project dir and docker log for one case.
new_project() {
  project="$work/project-$1"
  mkdir -p "$project"
  touch "$project/.env"
  log="$project/docker.log"
}

# deploy <image> runs the script as the verifier does.
deploy() {
  PATH="$work/bin:$PATH" FAKE_DOCKER_LOG="$log" WD_PROJECT_DIR="$project" \
    DEPLOY_IMAGE="$1" DEPLOY_VERSION=v1.2.3 DEPLOY_REPOSITORY=HEROgold/Winter-Dragon-Bot DEPLOY_SHA=abc \
    "$script" </dev/null >"$project/out.log" 2>&1
}

check() {
  if eval "$2"; then
    echo "ok   $1"
  else
    echo "FAIL $1"
    sed 's/^/     | /' "$project/out.log"
    failures=$((failures + 1))
  fi
}

new_project deploys
deploy "$image_a"
status=$?
check "a pinned image deploys" '[[ $status -eq 0 ]]'
check "writes WD_IMAGE and WD_VERSION to .env.deploy" '[[ "$(cat "$project/.env.deploy")" == "$env_a" ]]'
check "pulls the image" 'grep -qx "pull --quiet $image_a" "$log"'
check "starts bot and web, which run backup and migrate first" \
  'grep -qx "$compose_args up -d --wait --wait-timeout 540 bot web" "$log"'
check "never runs git" '! grep -q git "$log"'

new_project keeps-prev
deploy "$image_a"
deploy "$image_b"
check "second deploy keeps the first in .env.deploy.prev" '[[ "$(cat "$project/.env.deploy.prev")" == "$env_a" ]]'
check "second deploy writes the new image" '[[ "$(cat "$project/.env.deploy")" == "$env_b" ]]'

new_project rollback
deploy "$image_a"
FAKE_UP_FAILS=2 deploy "$image_b"
status=$?
check "failed up exits non-zero" '[[ $status -ne 0 ]]'
check "failed up prints migrate, bot and web logs" 'grep -qx "$compose_args logs --tail 50 migrate bot web" "$log"'
check "failed up restores the previous image" '[[ "$(cat "$project/.env.deploy")" == "$env_a" ]]'
check "rollback skips backup and migrate" 'grep -qx "$compose_args up -d --wait --wait-timeout 240 --no-deps bot web" "$log"'

new_project first-deploy-fails
FAKE_UP_FAILS=1 deploy "$image_a"
status=$?
check "a failed first deploy exits non-zero" '[[ $status -ne 0 ]]'
check "a failed first deploy has nothing to roll back to" '[[ $(grep -c " up " "$log") -eq 1 ]]'
check "a failed first deploy forgets its image" '[[ ! -e "$project/.env.deploy" ]]'
deploy "$image_b"
check "the deploy after a failed first one has no rollback target" '[[ ! -e "$project/.env.deploy.prev" ]]'

new_project bad-version
PATH="$work/bin:$PATH" FAKE_DOCKER_LOG="$log" WD_PROJECT_DIR="$project" DEPLOY_IMAGE="$image_a" \
  DEPLOY_VERSION=$'v1\nWD_IMAGE=evil' "$script" </dev/null >"$project/out.log" 2>&1
check "drops a version that isn't a plain v<version>" \
  '[[ "$(cat "$project/.env.deploy")" == "$(printf "WD_IMAGE=%s\nWD_VERSION=" "$image_a")" ]]'

for bad in \
  "ghcr.io/herogold/winter-dragon-bot:latest" \
  "ghcr.io/someone/winter-dragon-bot@sha256:$(printf 'a%.0s' {1..64})" \
  ""; do
  new_project "bad-image-$RANDOM"
  deploy "$bad"
  status=$?
  check "rejects image '$bad'" '[[ $status -ne 0 && ! -s "$log" && ! -e "$project/.env.deploy" ]]'
done

if (( failures )); then
  echo "$failures failure(s)"
  exit 1
fi
echo "all passed"
