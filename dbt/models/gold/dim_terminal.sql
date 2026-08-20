{#
  Direct port of etl_core/gold/dim_terminal.py. Distinct parking terminals
  referenced in the case table (single role - no UNION needed here, unlike
  dim_agent/dim_assignment_group).
#}

select distinct
    parking_terminal_sys_id as terminal_sys_id,
    parking_terminal_name as terminal_name
from {{ source('silver', 'sn_customerservice_case') }}
where parking_terminal_sys_id is not null
