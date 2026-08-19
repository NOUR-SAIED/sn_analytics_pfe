{#
  History retention for sn_customerservice_case (audit finding #1 in
  CLAUDE.md: bronze/silver upsert by sys_id, gold TRUNCATE+INSERTs every
  run - latest state only, no history anywhere). This snapshot is purely
  additive: it reads silver.sn_customerservice_case as-is and writes to a
  NEW table (snapshots.sn_case_snapshot). It does not touch bronze, silver,
  or any gold table, and nothing downstream depends on it yet - see
  docs/dbt_onboarding.md for what's deliberately deferred.

  Strategy: timestamp, keyed on sys_updated_on (verified 100% populated).
  unique_key is sys_id, matching the natural key used everywhere else in
  the pipeline (etl_core loaders, gold dim/fact builders).
#}
{% snapshot sn_case_snapshot %}

{{
    config(
      target_schema='snapshots',
      unique_key='sys_id',
      strategy='timestamp',
      updated_at='sys_updated_on',
    )
}}

select *
from {{ source('silver', 'sn_customerservice_case') }}

{% endsnapshot %}
