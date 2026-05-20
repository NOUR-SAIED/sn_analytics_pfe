# Gold Layer — Computed Fields

> Computed/derived fields are NOT calculated in silver.
> They are deferred to the gold layer where business logic lives.
> This keeps silver clean — just data, no calculations.

---

## Computed Fields to Implement in Gold

These fields require business logic (time calculations, aggregations, KPIs)
and should be computed when building the gold/dashboard layer.

| Field | Formula | Source Table |
|---|---|---|
| `response_time_s` | `first_response_time - opened_at` | silver.incidents |
| `resolution_time_s` | `resolved_at - opened_at` | silver.incidents |
| `assign_time_s` | `assigned_at - opened_at` | silver.incidents |
| `closure_lag_s` | `closed_at - resolved_at` | silver.incidents |

---

## Notes

- All timestamps are stored as `TIMESTAMPTZ` in silver.incidents
- Computed fields return seconds as `BIGINT`
- Business-hours SLA calculation (vs calendar time) requires `task_sla` table — not yet available
- When adding new computed fields, add them to this document with formula and source table

---

## Example Gold SQL

```sql
SELECT
    sys_id,
    opened_at,
    first_response_time,
    resolved_at,
    closed_at,
    EXTRACT(EPOCH FROM (first_response_time - opened_at))::BIGINT AS response_time_s,
    EXTRACT(EPOCH FROM (resolved_at - opened_at))::BIGINT AS resolution_time_s,
    EXTRACT(EPOCH FROM (assigned_at - opened_at))::BIGINT AS assign_time_s,
    EXTRACT(EPOCH FROM (closed_at - resolved_at))::BIGINT AS closure_lag_s
FROM silver.incidents
WHERE opened_at IS NOT NULL
  AND first_response_time IS NOT NULL;
```

Last updated: 2026-05-20