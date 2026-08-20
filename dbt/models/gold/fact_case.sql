{#
  Direct port of etl_core/gold/fact_case.py - the last table in the
  Python -> dbt gold migration (see docs/dbt_onboarding.md for the full
  per-table log). One row per case; SLA metrics pivoted from
  silver.task_sla (up to 2 rows per case, one per SLA type) into wide
  columns before joining, exactly as the original sla_pivot CTE did - this
  avoids join fan-out (without the pivot, a case with both SLA types would
  produce 2 fact rows and silently double every downstream COUNT/SUM).

  Note what does and doesn't get a real ref()/JOIN here, same as the
  original: dim_date IS joined (its date_key is actually looked up).
  dim_agent/dim_assignment_group/dim_terminal are NOT joined - fact_case
  just carries the raw sys_id values straight through from the case table
  (those dims share the same sys_ids by construction). The original Python
  version enforced that relationship with FK constraints instead of a
  join; here it's enforced by the `relationships` dbt tests in
  models/gold/_gold.yml, which is why those 3 dims aren't ref()'d in this
  file even though fact_case's grain genuinely depends on them.
#}

with sla_pivot as (
    select
        ts.task_sys_id,
        max(case when cs.name = '{{ var("response_sla_name") }}' then ts.duration end)
            as response_sla_duration,
        max(case when cs.name = '{{ var("response_sla_name") }}' then ts.percentage end)
            as response_sla_percentage,
        bool_or(case when cs.name = '{{ var("response_sla_name") }}' then ts.has_breached end)
            as response_sla_has_breached,
        max(case when cs.name = '{{ var("resolution_sla_name") }}' then ts.duration end)
            as resolution_sla_duration,
        max(case when cs.name = '{{ var("resolution_sla_name") }}' then ts.percentage end)
            as resolution_sla_percentage,
        bool_or(case when cs.name = '{{ var("resolution_sla_name") }}' then ts.has_breached end)
            as resolution_sla_has_breached
    from {{ source('silver', 'task_sla') }} ts
    join {{ source('silver', 'contract_sla') }} cs on ts.sla_sys_id = cs.sys_id
    where cs.name in ('{{ var("response_sla_name") }}', '{{ var("resolution_sla_name") }}')
    group by ts.task_sys_id
)

select
    c.sys_id as case_id,
    c.sys_id,
    c.case_number,

    do_.date_key as opened_date_key,
    da_.date_key as assigned_date_key,
    dfr_.date_key as first_response_date_key,
    dr_.date_key as resolved_date_key,
    dc_.date_key as closed_date_key,
    docc_.date_key as occurrence_date_key,

    c.state_code,
    c.state_label,
    c.auto_close,
    c.approval_code,
    c.approval_label,

    c.priority_code,
    c.priority_label,
    c.urgency_code,
    c.urgency_label,
    c.impact_code,
    c.impact_label,

    c.category_label,
    c.subcategory_label,
    c.u_sub_category,
    c.cause,
    c.resolution_code,
    c.resolution_code_label,
    c.sub_code,
    c.sub_code_label,

    c.assigned_to_sys_id,
    c.opened_by_sys_id,
    c.resolved_by_sys_id,
    c.owned_by_sys_id,
    c.last_assignee_sys_id,

    c.assignment_group_sys_id,
    c.last_assignment_group_sys_id,
    c.parking_terminal_sys_id,

    c.device_type_label,

    sp.response_sla_duration,
    sp.response_sla_percentage,
    sp.response_sla_has_breached,
    sp.resolution_sla_duration,
    sp.resolution_sla_percentage,
    sp.resolution_sla_has_breached,

    c.time_worked,
    c.reassignment_count,

    c.sys_created_on,
    c.sys_updated_on,

    now() as loaded_at

from {{ source('silver', 'sn_customerservice_case') }} c
left join sla_pivot sp on c.sys_id = sp.task_sys_id

left join {{ ref('dim_date') }} do_
    on do_.full_date = c.opened_at::date
left join {{ ref('dim_date') }} da_
    on da_.full_date = c.assigned_at::date
left join {{ ref('dim_date') }} dfr_
    on dfr_.full_date = c.first_response_time::date
left join {{ ref('dim_date') }} dr_
    on dr_.full_date = c.resolved_at::date
left join {{ ref('dim_date') }} dc_
    on dc_.full_date = c.closed_at::date
left join {{ ref('dim_date') }} docc_
    on docc_.full_date = c.u_date_of_occurrence
