# Deploying Winter Dragon

A version bump on `main` deploys itself. After the Test workflow passes, `release.yml`:

1. Tags `v<version>` and creates the GitHub release and the Sentry release for that version.
2. Builds the image from the commit the Test run passed and pushes it to
   `ghcr.io/herogold/winter-dragon-bot`, tagged `v<version>` and `sha-<commit>`. The job's
   `digest` output pins it. The build runs before the tag is made, so a failed build leaves no
   tag and the next run on `main` tries again.
3. Runs the deploy job in the `production` environment, so that environment's protection rules
   apply (add a required reviewer there to gate deploys), then notifies the VPS through
   [deploy-notifier](https://github.com/HEROgold/deploy-notifier) at
   `https://deploy.herogold.nl/hooks/winter-dragon` with the image pinned by digest and the version
   `v<version>`. The verifier runs `deploy-wd.sh`.
4. Fetches `https://dragon.herogold.nl/` until it answers 200. The landing page reads the
   database, so that covers Traefik, `web`, `migrate` and `postgres`.

`deploy-wd.sh` pulls the image, writes `WD_IMAGE` and `WD_VERSION` to `.env.deploy`, and runs
`docker compose up -d --wait bot web`. That runs `backup`, then `migrate`, then starts the bot and
the dashboard and waits for their healthchecks. If any of that fails, the script prints the logs
of `migrate`, `bot` and `web`, puts the previous `.env.deploy` back, and starts the previous image
without running `backup` or `migrate` again. The job then fails.

Compose passes `WD_VERSION` to the containers as `SENTRY_RELEASE`, so Sentry events carry the
version that is running, also after a rollback.

The deploy never runs `git pull` and never builds on the server.

## Migrations

The rollback doesn't undo migrations. Each revision must keep the previous image working: add
columns and tables in one release, and remove what the old code still reads in a later one.

## On the VPS (ubuntu-4gb-hel1-1)

Everything runs as `herogold`. The stack's compose project is `winter-dragon-bot`, and the
dashboard is public at `https://dragon.herogold.nl` through the Traefik on `traefik_network`.

```text
~/Winter-Dragon-Bot/            this app
├── compose.yml                 deploy/compose.yml
├── deploy-wd.sh                deploy/deploy-wd.sh (executable)
├── backup-db.sh                scripts/backup-db.sh
├── .env                        DB_PASSWORD=… (0600), the same password as database.ini
├── *.ini                       bot.ini, config.ini, cogs.ini, database.ini, sentry.ini, dashboard.ini,
│                               archive.ini (0600)
├── logs/                       owned by uid 10001, the image's user
├── backups/                    pre-migrate-*.dump and daily-*.dump, the newest 14 of each
├── .env.deploy                 written by deploy-wd.sh: WD_IMAGE=ghcr.io/…@sha256:… and WD_VERSION=v…
└── .env.deploy.prev            the deploy before that, for rollback
~/deploy-notifier/verifier/     the deploy verifier, a container behind Traefik
├── config.toml                 includes deploy/verifier.toml's [apps.winter-dragon]
└── compose.override.yml        mounts ~/Winter-Dragon-Bot at the same path
```

### One-time setup

1. Files. Copy `deploy/compose.yml`, `deploy/deploy-wd.sh` and `scripts/backup-db.sh` into
   `~/Winter-Dragon-Bot`. The verifier runs the deploy script as uid 1000 with the docker group:

   ```sh
   cd ~/Winter-Dragon-Bot
   chmod 755 deploy-wd.sh
   mkdir -p logs backups
   ```

   Copy them again when they change. The deploy doesn't update them.

2. Settings. `.env` holds `DB_PASSWORD` (`openssl rand -hex 32`). The bot reads its database
   URL from `database.ini`, not from the environment, so `database.ini` needs `host = postgres`
   and the same password. `sentry.ini` has `environment = production`. `dashboard.ini` has
   `host = 0.0.0.0`, `port = 8001` and `public_url = https://dragon.herogold.nl`, and the Discord
   application lists `https://dragon.herogold.nl/auth/discord/callback` as an OAuth2 redirect.
   `logs/` belongs to uid 10001, the user the image runs as.

3. Registry access. After the first release pushes the GHCR package, set it to public in its
   package settings. The server then pulls it without a login.

4. Deploy verifier. `[apps.winter-dragon]` from `deploy/verifier.toml` is already in
   `~/deploy-notifier/verifier/config.toml`, and `compose.override.yml` already mounts
   `/home/herogold/Winter-Dragon-Bot`. A bind mount follows the directory it was created on, so
   after the cutover moves the old checkout aside, recreate the verifier and check what it sees:

   ```sh
   cd ~/deploy-notifier/verifier
   docker compose -f compose.example.yml -f compose.override.yml up -d --force-recreate
   docker exec verifier-verifier-1 ls /home/herogold/Winter-Dragon-Bot
   ```

5. GitHub. The repository needs the `production` environment and the repository variable
   `DEPLOY_URL` set to `https://deploy.herogold.nl/hooks/winter-dragon`.

Without a token, `curl -i -X POST https://deploy.herogold.nl/hooks/winter-dragon` answers 401.

## Deploying by hand

Pick the digest from the release run's `new-release` job output, or from the package page:

```sh
cd ~/Winter-Dragon-Bot
printf 'WD_IMAGE=%s\nWD_VERSION=%s\n' ghcr.io/herogold/winter-dragon-bot@sha256:… v… > .env.deploy
docker compose -f compose.yml --env-file .env --env-file .env.deploy up -d --wait bot web
```

To roll back by hand, `mv .env.deploy.prev .env.deploy` and run the same `up` with `--no-deps`.

The archive isn't part of a deploy. Start it with the same command plus `--profile archive up -d archive`.

## Testing the script

`bash deploy/test-deploy-wd.sh` runs `deploy-wd.sh` against a fake `docker` in a scratch directory.
