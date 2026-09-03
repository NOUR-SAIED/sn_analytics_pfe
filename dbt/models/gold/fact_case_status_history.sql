{#
  Closes the gap flagged in CLAUDE.md under "Cube semantic layer": Cube only
  modeled fact_case's grain (one row per case, latest state only); nothing
  built on snapshots.sn_case_snapshot (the SCD2 history from dbt/snapshots/
  sn_case_snapshot.sql) was queryable anywhere. This is that model.

  Grain: one row per (case, contiguous period the case spent with one
  state_label) - NOT one row per case. A case that has been Closed the whole
  time it's been tracked has exactly 1 row here; a case that went
  New -> Assigned -> Resolved -> Closed has 4, one per stage.

  This is deliberately a separate fact table, not a merge into fact_case:
  the grain is genuinely different (fact_case is case-grain; this is
  case-stage-grain), and mixing them would force every fact_case consumer to
  either de-dupe or accept incorrect row multiplication - the same fan-out
  problem the sla_pivot CTE in fact_case.sql exists to avoid, just for a
  different join.

  Why this is almost mechanical: a dbt timestamp-strategy snapshot already
  stores exactly "when did this become true" (dbt_valid_from) and "when did
  it stop being true" (dbt_valid_to, NULL if still current) for every
  tracked column as a group - so each snapshot row already *is* one state
  period. No window-function reconstruction needed; this model is close to
  a straight projection, not a rebuild.

  Known data-maturity caveat (be upfront about this, don't oversell it):
  as of the session that added this model, `snapshots.sn_case_snapshot` has
  captured almost no *real* state changes yet - only one case has more than
  one version, and that one extra version was a manual test edit (see the
  "verified by manually editing a test row" note on the snapshot in
  CLAUDE.md), not organic ServiceNow activity. That means today this model
  mostly returns one open-ended "current state" row per case with a growing
  duration - which is the CORRECT output for data where the snapshot has
  only run a few times, not a bug. It becomes actually useful for
  time-per-stage analysis once the daily `dbt_snapshot_sn_case` task
  (dags/sn_bronze_to_silver.py) has run across enough real state transitions
  to accumulate history. The model and the Cube layer on top of it are
  built and tested now so that data is captured and query-ready starting
  today, instead of only after someone notices the gap later.
#}

select
    dbt_scd_id                                      as stage_id,
    sys_id                                           as case_id,
    case_number,
    state_code,
    state_label,
    dbt_valid_from                                   as stage_started_at,
    dbt_valid_to                                     as stage_ended_at,
    dbt_valid_to is null                             as is_current_stage,
    extract(
        epoch from (coalesce(dbt_valid_to, now()) - dbt_valid_from)
    )                                                 as stage_duration_seconds,
    row_number() over (
        partition by sys_id order by dbt_valid_from
    )                                                 as stage_sequence

from {{ ref('sn_case_snapshot') }}
