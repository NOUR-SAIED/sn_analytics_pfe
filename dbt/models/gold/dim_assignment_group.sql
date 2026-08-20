{#
  Direct port of etl_core/gold/dim_assignment_group.py. Distinct assignment
  groups referenced across the case table's 2 group-role columns
  (assignment_group, last_assignment_group).
#}

select distinct sys_id as assignment_group_sys_id, name as assignment_group_name
from (
    select assignment_group_sys_id as sys_id, assignment_group_name as name
    from {{ source('silver', 'sn_customerservice_case') }}
    where assignment_group_sys_id is not null

    union

    select last_assignment_group_sys_id as sys_id, last_assignment_group_name as name
    from {{ source('silver', 'sn_customerservice_case') }}
    where last_assignment_group_sys_id is not null
) combined
