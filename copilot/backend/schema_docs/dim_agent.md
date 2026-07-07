# gold.dim_agent

Agent lookup table built from distinct people referenced by cases.

## Fields
- `agent_sys_id`: ServiceNow sys_id and primary key.
- `agent_name`: Best available display name.
- `email`: Agent email when available.
- `mobile_phone`: Agent mobile number when available.

## How to use it
- Join from `fact_case` on agent sys_id fields such as `assigned_to_sys_id` or `opened_by_sys_id`.
- Prefer this table when you need a stable person dimension rather than repeated names in the fact.
- If a record is missing contact data, `agent_name` still provides the fallback identity.
