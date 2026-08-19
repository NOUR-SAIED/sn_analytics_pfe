# dbt onboarding — what's here, what's proven, what's deliberately not done yet

This is the project's first use of dbt. It exists to fix audit finding #1 in `CLAUDE.md`: bronze and
silver upsert by `sys_id` (latest state only), and every gold dim/fact is `TRUNCATE`+`INSERT` on every
run — a case's status/assignment history is nowhere. dbt **snapshots** (SCD Type 2) fix that, reading
the existing silver table as-is with no changes to `etl_core/` or the Python pipeline.

## What exists right now

- `dbt/` — a dbt project, independent of the Python pipeline. Nothing in `etl_core/`, `dags/`
  (other than a comment, see below), or any bronze/silver/gold table was changed to build this.
- `dbt/models/staging/_sources.yml` — declares `silver.sn_customerservice_case` as a dbt source. dbt
  only reads it, never writes to it.
- `dbt/models/staging/_smoke_test.sql` — a trivial passthrough view, kept as a template for the next
  staging model. Not load-bearing; delete freely.
- `dbt/snapshots/sn_case_snapshot.sql` — the actual fix. Timestamp strategy keyed on `sys_updated_on`
  (verified 100% populated). Writes to a **new** table, `snapshots.sn_case_snapshot`, with dbt's
  standard `dbt_valid_from`/`dbt_valid_to` columns.
- `dbt/requirements.txt` — pins `dbt-postgres==1.11.0`, kept separate from the root `requirements.txt`
  on purpose (see the incident below).
- `.venv-dbt/` (gitignored, local only) — an isolated Python venv for running dbt from the Windows
  host. Kept separate from the existing `venv/` used for `etl_core` dev.

## What's been proven (same session, no multi-day wait needed)

Test data doesn't drift on its own, so validation had to simulate a change instead of waiting for one:

1. `dbt debug` — connects to the real running Postgres. ✅
2. `dbt run` on the smoke-test model — resolves `source()`, creates a real view, returns real silver
   rows. ✅
3. `dbt snapshot` — seeded `snapshots.sn_case_snapshot` with all 356 current case rows. ✅
4. **The actual proof:** manually flipped one test case's `state_label` and `sys_updated_on`, reran
   `dbt snapshot`, and confirmed exactly two versions of that row exist with correct
   `dbt_valid_from`/`dbt_valid_to` boundaries (the old row's `valid_to` exactly matches the new row's
   `valid_from`). Then reverted the test edit and snapshotted again — a clean 3-version history
   resulted. This is the mechanism working correctly; it doesn't need real data to ever change to be
   proven, only that *when* it changes, it's captured right. ✅

There's a cosmetic dbt-postgres warning on every snapshot run — `Data type of snapshot table timestamp
columns (DATETIME) doesn't match derived column 'updated_at' (DATETIMETZ)`. Checked directly with
`\d snapshots.sn_case_snapshot`: every relevant column (`sys_updated_on`, `dbt_updated_at`,
`dbt_valid_from`, `dbt_valid_to`) is actually `timestamp with time zone`, consistently. This is a known
false-positive in dbt-postgres's snapshot type-check heuristic, not a real type mismatch — documented
here so it doesn't cause alarm later.

## What's deliberately NOT done yet

- **No gold model reads from the snapshot yet.** No lifecycle-KPI fact table has been built on top of
  `snapshots.sn_case_snapshot`. That's real new capability worth its own planning session once dbt
  itself feels solid — not bundled into this cleanup pass.
- **Only `sn_customerservice_case` is snapshotted.** Dims (`dim_agent`, `dim_assignment_group`) are a
  cheap follow-on later, not required now.
- **Not wired into Airflow yet — see the incident below.**

## Incident: why this isn't wired into a DAG yet

The plan was to add a `BashOperator` task running `dbt snapshot` in `dags/sn_bronze_to_silver.py`,
right after the silver-load step for the case table, with `dbt-postgres` installed into the same
custom Airflow image (`dockerfile`) that already runs the rest of this pipeline.

That was tried, and rolled back. Installing `dbt-postgres` into that image pulled in `click==8.4.2`
as a transitive dependency (from `dbt-core`), overwriting the `click` version the image's pinned
Celery/Airflow (2.9.2) needs. Result: `airflow-worker` — the container that executes **every task in
this project** — crash-looped on startup (`celery.utils.nodenames.nodesplit` raised
`AttributeError: 'NoneType' object has no attribute 'split'`, a known symptom of Celery's click-based
CLI breaking against a too-new click).

This was caught and fixed within the same session (rebuilt the image without dbt, confirmed
`airflow-worker` returned to healthy, confirmed both live DAGs still parse with zero import errors),
but it's a real example of why "first contact with dbt" needs to stay cautious: installing dbt's
dependency tree into the same environment as an unrelated, sensitive service (here, Celery) is a
genuine collision risk, not a hypothetical one.

**`dags/sn_bronze_to_silver.py` currently has no dbt task** — it's back to exactly its pre-dbt state,
plus one explanatory comment pointing here. `docker-compose.yml` does mount `./dbt:/opt/airflow/dbt`
into the Airflow containers (harmless — it's just a bind mount, nothing is installed there), so the
project files are visible for a manual `docker exec` run if needed, but nothing runs automatically.

### Options for wiring this in safely (not decided yet — next conversation)

1. **A dedicated `dbt` container.** Its own lightweight image (e.g. `python:3.11-slim` +
   `dbt-postgres` only, no Airflow/Celery in it at all), added as its own `docker-compose.yml` service.
   Airflow triggers it via `DockerOperator` or a mounted Docker socket. Most isolated, zero risk of a
   repeat of this incident; adds a moderate amount of new infrastructure.
2. **`KubernetesPodOperator` / ECS-style external run** — overkill for this project's current scale
   (single-host Docker Compose), not recommended.
3. **Run dbt from the local `.venv-dbt/` on a schedule outside Airflow** (cron, or manually) until the
   project is ready to invest in option 1. Simplest, but loses Airflow's retry/observability/lineage
   for this step, and someone has to remember to run it.

Recommendation when this comes back up: option 1, scoped small (the container only needs
`dbt-postgres` and the `dbt/` folder — nothing else).
