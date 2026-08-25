{#
  Direct port of etl_core/gold/dim_agent.py. Collects every distinct agent
  sys_id referenced across the case table's 5 agent-role columns
  (assigned_to, opened_by, resolved_by, owned_by, last_assignee), enriched
  with name/email/phone from silver.sys_user when available.

  Not ported: the original's MIGRATE_SQL step (ALTER TABLE ... ADD COLUMN
  IF NOT EXISTS email/mobile_phone). That existed only because Python's
  CREATE TABLE IF NOT EXISTS doesn't evolve an existing table's schema -
  dbt's `table` materialization always rebuilds from this SELECT's actual
  output columns, so there's nothing to migrate.
#}

with agent_roles as (
    select assigned_to_sys_id as sys_id, assigned_to_name as name
    from {{ source('silver', 'sn_customerservice_case') }}
    where assigned_to_sys_id is not null

    union

    select opened_by_sys_id, opened_by_name
    from {{ source('silver', 'sn_customerservice_case') }}
    where opened_by_sys_id is not null

    union

    select resolved_by_sys_id, resolved_by_name
    from {{ source('silver', 'sn_customerservice_case') }}
    where resolved_by_sys_id is not null

    union

    select owned_by_sys_id, owned_by_name
    from {{ source('silver', 'sn_customerservice_case') }}
    where owned_by_sys_id is not null

    union

    select last_assignee_sys_id, last_assignee_name
    from {{ source('silver', 'sn_customerservice_case') }}
    where last_assignee_sys_id is not null
)

select distinct
    a.sys_id as agent_sys_id,
    case
        when u.name is not null and u.name !~ '^[0-9a-f]{32}$' then u.name
        when a.name is not null and a.name !~ '^[0-9a-f]{32}$' then a.name
        -- Both silver.sys_user and the case table's own denormalized name
        -- fell back to the raw sys_id - confirmed (2026-08-25) this means
        -- ServiceNow itself never resolved a display name for this user
        -- (sys_user query returned zero rows for them; likely deactivated
        -- or outside the extraction service account's ACL scope), not a
        -- join bug on our side. Show a readable placeholder instead of
        -- leaking the raw 32-char hex into dashboards/the Copilot agent.
        else 'Unknown Agent (' || right(a.sys_id, 6) || ')'
    end as agent_name,
    u.email,
    u.mobile_phone
from agent_roles a
left join {{ source('silver', 'sys_user') }} u on a.sys_id = u.sys_id
