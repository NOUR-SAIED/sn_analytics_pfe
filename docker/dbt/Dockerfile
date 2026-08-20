# Dedicated dbt image — deliberately separate from the Airflow image
# (`dockerfile` at repo root). Installing dbt-core into the Airflow image
# once broke Celery (a `click` version collision — see
# docs/dbt_onboarding.md for the postmortem). Keeping dbt's dependencies
# in their own, unrelated container makes that class of collision
# impossible: nothing in this image is shared with Airflow/Celery.
#
# The dbt project (dbt/) IS baked into this image (not bind-mounted at
# runtime). Why: Airflow's DockerOperator talks to the HOST's Docker
# daemon (via the socket mounted into airflow-worker), not a nested
# daemon — so any bind-mount source path it specifies must be a real path
# on the host, not a path inside airflow-worker's own container
# filesystem. That's a portability trap (hardcoded Windows paths baked
# into a DAG file) worth just avoiding. Baking the project in instead
# means: change a model -> rebuild this image -> Airflow uses the new
# image next run. Normal "build once, deploy" pattern, and one this
# project already uses for the Airflow image itself.
#
# For fast local iteration (no rebuild), run this image with an explicit
# `-v <host-path>/dbt:/opt/dbt` bind mount from your own shell instead -
# that overlays this COPY and works fine for manual testing.
FROM python:3.11-slim

WORKDIR /opt/dbt

# git: dbt checks for it (used only if a dbt package is ever pulled from a
# git repo - not the case here, but this keeps `dbt debug` fully green).
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY dbt/requirements.txt /opt/dbt/requirements.txt
RUN pip install --no-cache-dir -r /opt/dbt/requirements.txt

COPY dbt/ /opt/dbt/

# No CMD/ENTRYPOINT that runs anything by default — Airflow's DockerOperator
# supplies the actual command (e.g. `dbt snapshot`, `dbt run --select gold`)
# per task run, then removes the container.
