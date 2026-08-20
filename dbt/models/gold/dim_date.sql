{#
  Direct port of etl_core/gold/dim_date.py. One row per calendar day across
  a fixed range (see vars.date_dim_start/date_dim_end in dbt_project.yml).

  The original Python version used INSERT ... WHERE NOT EXISTS to stay
  idempotent against a table it only ever appended to. dbt's `table`
  materialization rebuilds the whole table from this SELECT every run
  instead (CREATE OR REPLACE under the hood) - for a fixed calendar range
  with no history to lose, a full rebuild is harmless and simpler than
  porting the append-only logic.
#}

with days as (
    select generate_series(
        '{{ var("date_dim_start") }}'::date,
        '{{ var("date_dim_end") }}'::date,
        '1 day'::interval
    ) as d
)

select
    (extract(year from d) * 10000
        + extract(month from d) * 100
        + extract(day from d))::integer as date_key,
    d::date as full_date,
    extract(year from d)::integer as year,
    extract(month from d)::integer as month,
    extract(day from d)::integer as day,
    extract(week from d)::integer as week,
    extract(dow from d)::integer as weekday
from days
