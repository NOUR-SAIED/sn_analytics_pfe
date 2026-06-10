# Documentation Overview

This folder collects the project notes that describe the data model, mappings, and computed fields used by the analytics pipeline.

## Superset in this repository

Apache Superset is not started from the main project Dockerfile. It has its own image and its own service block in `docker-compose.yml`.

### Why there is a separate Superset Dockerfile

The project already has a Dockerfile for the Airflow-based part of the stack. That Dockerfile builds the image used by the ETL services.

Superset has different runtime needs, so it uses a separate Dockerfile at `docker/superset/Dockerfile`:

- base image: `apache/superset:latest`
- extra dependency: `psycopg2-binary` so Superset can talk to PostgreSQL
- output: a custom Superset image tagged as `sn_analytics_superset:latest`

This is the image that Compose starts for `superset-init` and `superset-app`.

### How Docker Compose includes that Dockerfile

In `docker-compose.yml`, the Superset services use a shared build definition:

- build context: `./docker/superset`
- Dockerfile: `Dockerfile`
- image name: `sn_analytics_superset:latest`

That means Compose does two jobs:

1. Build the custom Superset image from `docker/superset/Dockerfile`.
2. Run containers from that image as `superset-init` and `superset-app`.

The two services share the same image, but they run different commands:

- `superset-init` runs migrations and creates the admin user, then exits.
- `superset-app` runs the web UI with `gunicorn` and stays up.

### What `superset_config.py` does

The file `docker/superset/superset_config.py` is Superset's local Python config.

It is mounted into the container and loaded through `PYTHONPATH=/app/pythonpath`, so Superset reads it at startup.

This file sets:

- `SECRET_KEY` for Flask/Superset session and cookie signing
- `SQLALCHEMY_DATABASE_URI` for the metadata database connection
- `CACHE_CONFIG` and `DATA_CACHE_CONFIG` for Redis-backed caching
- feature flags such as `ALERT_REPORTS`

### What `SQLALCHEMY_DATABASE_URI` means

`SQLALCHEMY_DATABASE_URI` is the connection string Superset uses for its own metadata database.

That database stores:

- users and roles
- dashboards and charts
- permissions
- saved queries and metadata
- migration state

The format is:

`postgresql+psycopg2://username:password@host:port/database`

In this project, the value is built from environment variables so the same config works in Compose without hardcoding credentials in Python.

### How the Superset runtime flow works

At startup, the stack behaves like this:

1. PostgreSQL starts.
2. Redis starts.
3. `superset-init` runs database migrations against the Superset metadata database.
4. `superset-init` creates the admin user.
5. `superset-init` exits successfully.
6. `superset-app` starts the Superset web server on port `8088`.

Once the app is running, you open it at `http://localhost:8088`.

### Important separation of responsibilities

- The custom Dockerfile controls what packages exist inside the Superset image.
- Docker Compose controls how containers are started and how they talk to each other.
- `superset_config.py` controls Superset behavior at runtime.
- PostgreSQL stores the metadata that Superset needs to function.

## Existing documentation files

- `data_dictionary.md` - field-level meaning of source and transformed data
- `data_mapping.md` - mapping between source fields and warehouse fields
- `gold_computed_fields.md` - derived fields used in the gold layer
