# Local Listmonk with Docker

The example Compose file runs a disposable Listmonk and PostgreSQL installation. It is intended for development; choose production credentials and deployment settings separately.

```sh
LISTMONK_ADMIN_USER=admin LISTMONK_ADMIN_PASSWORD=change-this-local-password \
  docker compose -f docs/listmonk-docker-compose.yml up -d
```

Visit `http://localhost:9000`, sign in with the credentials you supplied, and create an API user/token for the MCP. There is no assumed default dashboard password.

To exercise v7 beta.2 explicitly:

```sh
LISTMONK_IMAGE=listmonk/listmonk:v7.0.0-beta.2 \
LISTMONK_ADMIN_USER=admin LISTMONK_ADMIN_PASSWORD=change-this-local-password \
  docker compose -f docs/listmonk-docker-compose.yml up -d
```

The example binds Listmonk to localhost. PostgreSQL is kept on the Compose network. Database installation is idempotent; the startup command applies Listmonk upgrades. Back up an existing database before upgrading.

```sh
docker compose -f docs/listmonk-docker-compose.yml down
```

This stops the services and retains the database volume. To start completely fresh, remove the named volume deliberately.
