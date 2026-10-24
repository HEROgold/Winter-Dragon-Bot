# Deploying Winter Dragon

A version bump on `main` deploys itself. After the Test workflow passes, `release.yml`:

1. Tags `v<version>` and creates the GitHub release and the Sentry release for that version.
2. Builds the image and pushes it to `ghcr.io/herogold/winter-dragon-bot` (#293). The job's
   `digest` output pins it.
3. Runs the deploy job in the `production` environment, so that environment's protection rules
   apply (add a required reviewer there to gate deploys), then notifies the VPS through
   [deploy-notifier](https://github.com/HEROgold/deploy-notifier) at
   `https://deploy.herogold.nl/hooks/winter-dragon` with the image pinned by digest and the version
   `v<version>`. The verifier runs `deploy-wd.sh`.

`deploy-wd.sh` pulls the image, writes `WD_IMAGE` to `.env.deploy`, and runs
`docker compose up -d --wait bot web`. That runs `backup`, then `migrate`, then starts the bot and
the dashboard and waits for their healthchecks. If any of that fails, the script prints the logs
of `migrate`, `bot` and `web`, puts the previous `.env.deploy` back, and starts the previous image
without running `backup` or `migrate` again. The job then fails.

The deploy never runs `git pull` and never builds on the server.

## Migrations

The rollback doesn't undo migrations. Each revision must keep the previous image working: add
columns and tables in one release, and remove what the old code still reads in a later one.

## On the VPS (ubuntu-4gb-hel1-1)

Everything runs as `herogold`. The cutover (#295) creates the directory.

```text
~/Winter-Dragon-Bot/            this app
├── compose.yml                 deploy/compose.yml
├── deploy-wd.sh                deploy/deploy-wd.sh (executable)
├── .env                        DB_PASSWORD and the other stack settings (0600)
├── *.ini                       bot.ini, config.ini, cogs.ini, database.ini, sentry.ini, dashboard.ini
├── logs/
├── .env.deploy                 written by deploy-wd.sh: WD_IMAGE=ghcr.io/herogold/winter-dragon-bot@sha256:…
└── .env.deploy.prev            the deploy before that, for rollback
~/deploy-notifier/verifier/     the deploy verifier, a container behind Traefik
├── config.toml                 includes deploy/verifier.toml's [apps.winter-dragon]
└── compose.override.yml        mounts ~/Winter-Dragon-Bot at the same path
```

### One-time setup

1. Deploy script. The verifier runs it as uid 1000 with the docker group:

   ```sh
   cd ~/Winter-Dragon-Bot
   # copy deploy/deploy-wd.sh here, then:
   chmod 755 deploy-wd.sh
   chown herogold:herogold deploy-wd.sh
   ```

   Copy it again when `deploy/deploy-wd.sh` changes. The deploy doesn't update it.

2. Registry access. After the first release pushes the GHCR package, set it to public in its
   package settings. The server then pulls it without a login.

3. Deploy verifier. `[apps.winter-dragon]` from `deploy/verifier.toml` is already in
   `~/deploy-notifier/verifier/config.toml`, and `compose.override.yml` already mounts
   `/home/herogold/Winter-Dragon-Bot`. A bind mount follows the directory it was created on, so
   after the cutover moves the old checkout aside, recreate the verifier and check what it sees:

   ```sh
   cd ~/deploy-notifier/verifier
   docker compose -f compose.example.yml -f compose.override.yml up -d --force-recreate
   docker exec verifier-verifier-1 ls /home/herogold/Winter-Dragon-Bot
   ```

4. GitHub. The repository needs the `production` environment and the repository variable
   `DEPLOY_URL` set to `https://deploy.herogold.nl/hooks/winter-dragon`.

Without a token, `curl -i -X POST https://deploy.herogold.nl/hooks/winter-dragon` answers 401.

## Deploying by hand

Pick the digest from the release run's `new-release` job output, or from the package page:

```sh
cd ~/Winter-Dragon-Bot
printf 'WD_IMAGE=%s\n' ghcr.io/herogold/winter-dragon-bot@sha256:… > .env.deploy
docker compose -f compose.yml --env-file .env --env-file .env.deploy up -d --wait bot web
```

To roll back by hand, `mv .env.deploy.prev .env.deploy` and run the same `up` with `--no-deps`.

## Not done yet

- There is no smoke test after the notify. Whether Traefik routes the dashboard is still open in
  #293. If it does, add one to the deploy job that retries the dashboard's health URL, like nota's.
- The bot's `sentry_sdk.init` sets no `release`, so events only carry `v<version>` if the
  container gets `SENTRY_RELEASE`. `deploy/compose.yml` (#293) can pass it in.

## Testing the script

`bash deploy/test-deploy-wd.sh` runs `deploy-wd.sh` against a fake `docker` in a scratch directory.
