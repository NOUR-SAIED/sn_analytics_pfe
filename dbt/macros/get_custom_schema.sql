{#
  dbt's default generate_schema_name macro CONCATENATES a model's
  `+schema:` override with the profile's target schema (e.g. profile
  schema "dbt_scratch" + override "gold" = "dbt_scratch_gold") - a
  well-known first-contact surprise, and the reason the staging smoke-test
  model earlier this session deliberately avoided setting +schema at all.

  This is dbt's own documented override for the common case where you
  actually want the override to BE the final schema name, unqualified -
  which is what we need here: gold models must land in exactly `gold`
  (the schema Superset and the Copilot agent already query), not
  `dbt_scratch_gold`. Models with no +schema override still fall back to
  the profile's default target schema, unaffected.
#}
{#
  DBT_GOLD_VERIFY_SUFFIX is an escape hatch for safely verifying a gold
  model BEFORE it overwrites the real, live `gold` schema that Superset
  and the Copilot agent already query. Set it (e.g. "_verify") to redirect
  every +schema override into a side-by-side schema (gold -> gold_verify)
  for comparison; unset (the normal case) writes to the real schema.
  See docs/dbt_onboarding.md for the per-table migration/verification log.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- set default_schema = target.schema -%}
    {%- set verify_suffix = env_var('DBT_GOLD_VERIFY_SUFFIX', '') -%}
    {%- if custom_schema_name is none -%}
        {{ default_schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}{{ verify_suffix }}
    {%- endif -%}
{%- endmacro %}
