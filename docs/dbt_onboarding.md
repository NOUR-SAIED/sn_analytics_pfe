# dbt in this project — what it does, what it replaced, current state

dbt was introduced this session for two things:

1. **History retention** (audit finding #1 in `CLAUDE.md`): bronze/silver upsert by `sys_id`
   (latest state only), so a case's status/assignment history was nowhere. Fixed with a dbt
   **snapshot**.
2. **Replacing the hand-written SQL scattered across `etl_core/gold/*.py`** with proper, tested,
   version-controlled dbt **models** — the actual data-engineering-best-practices goal, not just the
   narrow history-retention slice. This migration is now **complete**: all 5 gold tables are
   dbt-built.

## Current state, in one sentence

`etl_core/gold/` no longer contains any table-building logic — only `db.py`/`loader.py` for the
schema-exists check and the `copilot_reader` grant, neither of which is dbt's job. Everything that
builds a `gold.*` table lives in `dbt/models/gold/`, runs automatically via Airflow
(`dags/gold_build.py`), and is checked by 28 dbt tests on every run.

## What's in `dbt/`

- `dbt/models/staging/_sources.yml` — declares the silver tables dbt reads (`sn_customerservice_case`,
  `sys_user`, `task_sla`, `contract_sla`). dbt only reads these, never writes to them.
- `dbt/models/staging/_smoke_test.sql` — a trivial passthrough view kept as a template. Not
  load-bearing.
- `dbt/snapshots/sn_case_snapshot.sql` — SCD Type 2 history on `sn_customerservice_case`. Timestamp
  strategy on `sys_updated_on`. Writes to `snapshots.sn_case_snapshot`. **Not yet read by anything
  downstream** — no lifecycle-KPI gold model has been built on top of it yet; that's real new
  capability, worth its own planning session.
- `dbt/models/gold/*.sql` — the 5 gold star-schema tables, one file each: `dim_date`, `dim_agent`,
  `dim_assignment_group`, `dim_terminal`, `fact_case`. Each is a direct, verified port of the Python
  builder it replaced (see the per-table migration log below). `dbt/models/gold/_gold.yml` holds the
  28 tests: `not_null`/`unique` on every dimension key, plus 13 `relationships` tests on `fact_case`
  replacing the original hard FK constraints.
- `dbt/dbt_project.yml` — `vars.response_sla_name`/`resolution_sla_name` (were Python constants in
  `etl_core/gold/config.py`) and `vars.date_dim_start`/`date_dim_end` (were `DATE_DIM_START`/`END`).
  Gold models get `+schema: gold` and `+tags: ["gold"]`.
- `dbt/macros/get_custom_schema.sql` — overrides dbt's default schema-name generation, which otherwise
  concatenates a model's `+schema` override with the profile's target schema
  (`dbt_scratch` + `gold` → `dbt_scratch_gold`). Also adds a `DBT_GOLD_VERIFY_SUFFIX` env-var escape
  hatch: set it to redirect every gold model into a side-by-side schema (e.g. `gold_verify`) for
  comparison before ever touching the real `gold` schema. This is how every table in the migration was
  verified — built into `gold_verify`, diffed row-for-row against the live table, only cut over once
  confirmed identical.
- `docker/dbt/Dockerfile` — a dedicated image (`python:3.11-slim` + `dbt-postgres` + `git`), with the
  `dbt/` project baked in at build time. Deliberately has zero Airflow/Celery dependencies — see the
  incident below for why that matters.
- `.venv-dbt/` (gitignored, local only) — isolated Python venv for running dbt from the Windows host
  during development/verification, separate from the `venv/` used for `etl_core`.

## How it's wired into Airflow

Two DAGs run dbt now, both via `DockerOperator` (a fresh, disposable container from the
`sn_analytics-dbt` image per task run, removed when done — see the incident below for why not a
`BashOperator` installing dbt directly into Airflow's image):

- **`dags/sn_bronze_to_silver.py`** — `dbt_snapshot_sn_case` task, right after
  `verify_sn_customerservice_case`. Runs `dbt snapshot --select sn_case_snapshot`.
- **`dags/gold_build.py`** — `dbt_run_gold` (`dbt run --select gold`) → `dbt_test_gold`
  (`dbt test --select gold`) → `grant_copilot_reader_access` (still Python — a Postgres `GRANT` for an
  unrelated role, not a dbt concern). dbt's own dependency graph decides build order for the 5 gold
  models (the 4 dims, then `fact_case`) — no manual sequencing needed, unlike the old
  `etl_core/gold/pipeline.py`, which is now deleted.

## Incident: why dbt isn't installed into the Airflow image

Early in this session, the plan was to install `dbt-postgres` directly into the same custom Airflow
image (`dockerfile`) that runs Celery. That broke Celery: `dbt-core` pulled in `click==8.4.2` as a
transitive dependency, overwriting the `click` version this project's pinned Celery/Airflow (2.9.2)
needs. `airflow-worker` — the container that executes every task in this project — crash-looped on
startup (`celery.utils.nodenames.nodesplit` raised `AttributeError: 'NoneType' object has no attribute
'split'`, a known symptom of Celery's click-based CLI breaking against a too-new click).

Caught and reverted within the same session. The actual fix, done properly afterward: a **dedicated**
dbt image (`docker/dbt/Dockerfile`) with zero Airflow/Celery dependencies at all, triggered from
Airflow via `DockerOperator` over the Docker socket (mounted into `airflow-worker` only, not
scheduler/webserver). Verified after adding the official `apache-airflow-providers-docker` package to
Airflow's image: every dependency was already satisfied by packages already present — nothing new
installed, `click` stayed at `8.1.7`, `airflow-worker` stayed healthy throughout.

## Per-table gold migration log

Each table was migrated the same way: build into a side-by-side `gold_verify` schema
(`DBT_GOLD_VERIFY_SUFFIX=_verify`), diff row-for-row against the live Python-built table, cut over only
once confirmed identical, add dbt tests, delete the Python builder, re-verify downstream consumers.

1. **`dim_date`** — zero dependencies, first migrated. 4018/4018 rows identical. Cutover dropped 6 FK
   constraints `fact_case` had pointing at it (expected — see "constraints" below).
2. **`dim_agent`** — 12/12 rows identical. Dropped 5 FKs from `fact_case`.
3. **`dim_assignment_group`** — 4/4 rows identical. Dropped 2 FKs.
4. **`dim_terminal`** — 13/13 rows identical. Dropped 1 FK.
5. **`fact_case`** — the big one: the `sla_pivot` CTE (pivots `silver.task_sla` to avoid join fan-out)
   plus 6 `dim_date` lookups. 356/356 rows identical (excluding `loaded_at`, a `now()` timestamp that
   necessarily differs between build runs). Nothing references `fact_case` via FK, so no constraints
   were dropped by this cutover.

## Constraints: dbt tests instead of hard FKs — a deliberate choice, not a downgrade

Plain dbt `table` materialization doesn't emit `PRIMARY KEY`/`REFERENCES` DDL the way the old
`CREATE TABLE` statements in `etl_core/gold/config.py` did. Rather than lose that integrity checking,
`dbt/models/gold/_gold.yml` declares it as dbt tests instead: `not_null`/`unique` on every dimension
key, `relationships` tests on all 13 of `fact_case`'s role columns (date, agent, assignment group,
terminal). Run via `dbt test`, checked automatically on every `gold_build` DAG run — genuinely more
coverage than the original 8 hard FK constraints had, since every role column is now checked, not just
the ones someone remembered to add a `REFERENCES` to.

## Still open / deliberately deferred

- **Cube semantic layer** — not started. Sits in front of the now-dbt-built gold schema; repoints
  Superset's SQL Lab connection and the Copilot agent's `run_sql`. Explicitly bucketed into the
  dashboard/agent conversation, not this migration.
- **No gold model reads from `snapshots.sn_case_snapshot` yet** — the history-retention snapshot exists
  and is proven correct, but nothing queries it. A lifecycle-KPI fact table on top of it is real new
  capability, not part of this migration.
- **Dims aren't snapshotted** — only `sn_customerservice_case` has history tracking. Cheap follow-on
  later if needed.
- **Incremental extraction watermark** (audit finding #2) — unrelated to dbt, still not started, low
  priority while the data is static test data.
