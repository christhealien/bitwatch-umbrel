# bitwatch-umbrel

[Bitwatch](https://github.com/zapomatic/bitwatch) (MIT, by Zap-O-Matic) for Umbrel, packaged for the
[Bitcoin-Umbrel-APPS](https://github.com/christhealien/Bitcoin-Umbrel-APPS) store as **Bitwatch (blake2b)**:

- **Gotify alerts**: Integrations page gets a Gotify section (server address, application token, priority, tap-to-open
  link). Saving sends a test message. Alerts go to Gotify and Telegram (if set), deduplicated like upstream's.
- **blake2b look**: black, white and greys; status colours only for good / warning / failure.
- Uses the **Mempool (blake2b)** app on the same Umbrel by default (`MEMPOOL_API`, first start only).

How it builds: `.github/workflows/image.yml` checks out `zapomatic/bitwatch` at `UPSTREAM_REF`, runs
`tools/patch.py` (copies `overlay/`, patches the server and the Integrations page, recolours the client), builds
upstream's own Dockerfile for amd64 and arm64, publishes `ghcr.io/christhealien/blake2b-bitwatch:<version>` and copies
`blake2b-bitwatch/` into the store.

Release: bump `version` in `blake2b-bitwatch/umbrel-app.yml` and the image tag in `docker-compose.yml`, then push a
tag `bitwatch-v<version>`. To follow a new upstream release, change `UPSTREAM_REF`.
