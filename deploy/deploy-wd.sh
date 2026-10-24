#!/usr/bin/env bash
# The deploy-notifier command for Winter Dragon. It runs the notified image, with
# backup and migrations first. It lives in ~/Winter-Dragon-Bot on the VPS. The
# verifier is a container with that directory mounted at the same path, and it
# runs this script after it validates DEPLOY_IMAGE against the image_pattern of
# [apps.winter-dragon]. The script exits 0 when the deploy succeeded and
# non-zero otherwise.
set -euo pipefail

project_dir=${WD_PROJECT_DIR:-/home/herogold/Winter-Dragon-Bot}
image_pattern='^ghcr\.io/herogold/winter-dragon-bot@sha256:[0-9a-f]{64}$'

cd "$project_dir"

# The verifier already checked DEPLOY_IMAGE; checking again costs nothing.
[[ "${DEPLOY_IMAGE:-}" =~ $image_pattern ]] || { echo "image '${DEPLOY_IMAGE:-}' is not a pinned Winter Dragon image" >&2; exit 1; }

# The verifier runs this with no HOME. The image is public, so a pull needs no
# login, but docker still wants a config dir.
export DOCKER_CONFIG=${DOCKER_CONFIG:-/home/herogold/.docker}

docker pull --quiet "$DEPLOY_IMAGE"

# compose.yml passes WD_VERSION to Sentry as the release. It goes into an env
# file, so only a plain version string is kept.
version=${DEPLOY_VERSION:-}
[[ "$version" =~ ^v[0-9A-Za-z.+-]+$ ]] || version=

[[ -f .env.deploy ]] && cp .env.deploy .env.deploy.prev
printf 'WD_IMAGE=%s\nWD_VERSION=%s\n' "$DEPLOY_IMAGE" "$version" >.env.deploy.tmp
mv .env.deploy.tmp .env.deploy

compose() { docker compose -f compose.yml --env-file .env --env-file .env.deploy "$@"; }

# `up bot web` runs backup and then migrate, because bot and web wait for
# migrate to complete. --wait blocks until both healthchecks pass. The verifier
# kills this script after 900 s. The two waits take at most 780 s, which leaves
# 120 s for the pull.
if ! compose up -d --wait --wait-timeout 540 bot web; then
  echo "deploy of $DEPLOY_IMAGE failed, rolling back" >&2
  compose logs --tail 50 migrate bot web >&2 || true
  if [[ -f .env.deploy.prev ]]; then
    # Migrations are not rolled back, so each revision must keep the previous
    # image working. Expand first, and contract in a later release. --no-deps
    # skips backup and migrate, because the previous image's `upgrade head`
    # would fail on a database that is already at the newer revision.
    mv .env.deploy.prev .env.deploy
    compose up -d --wait --wait-timeout 240 --no-deps bot web || true
  else
    # Nothing ran before this image. Forget it, so the next deploy doesn't keep
    # it as the image to roll back to.
    rm -f .env.deploy
  fi
  exit 1
fi
echo "deployed $DEPLOY_IMAGE as ${DEPLOY_VERSION:-?} from ${DEPLOY_REPOSITORY:-?} at ${DEPLOY_SHA:-?}"
