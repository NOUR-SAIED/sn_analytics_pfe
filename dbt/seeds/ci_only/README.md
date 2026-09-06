# CI-only synthetic fixtures — DO NOT run against a real target

These 4 CSVs are small, entirely made-up `silver.*` rows (fake sys_ids,
fake names on an `@example.test` domain — a domain reserved by RFC 2606
specifically so it's obviously never a real address). They exist for one
reason: giving the CI `dbt build` job something to build the gold layer
against, since GitHub Actions' Postgres service container starts empty.

**Never run `dbt seed` against `dev` or any real target.** These seeds are
tagged `ci_only` in `dbt_project.yml` specifically so a bare `dbt seed`
does not touch them — CI invokes `dbt seed --select tag:ci_only` explicitly,
and that's the only place this should ever run. Seeding these 8 fake cases
on top of the real 356+ in the live `silver.sn_customerservice_case` would
corrupt real analytics.

## What the 8 cases in `sn_customerservice_case.csv` cover

Picked to exercise real code paths this project has actual bugs/tests
for, not just "some rows exist":

- `case-0001` — a clean, fully-closed case, SLA met on both response and
  resolution.
- `case-0002` — response SLA breached, resolution met (independent flags).
- `case-0003` — still open (`state_label = New`), **zero rows in
  `task_sla.csv`** — exercises the `LEFT JOIN sla_pivot` producing NULLs,
  which is what the breach-rate NULL-handling fix (CLAUDE.md, "Cube
  semantic layer" §2.4-equivalent) depends on: a case with no applicable
  SLA must fall out of `AVG()`, not silently count as "didn't breach".
- `case-0004` — both SLA types breached.
- `case-0005` — reassigned twice: `assigned_to` ≠ `last_assignee`, and
  `assignment_group` ≠ `last_assignment_group` — exercises that the 5
  agent-roles and 2 group-roles in `dim_agent`/`dim_assignment_group`
  actually resolve to *different* rows, not just the same one 5 times.
- `case-0006` — unassigned (`assigned_to_sys_id` is blank) — exercises
  `dim_agent`'s `where ... is not null` filters and `fact_case`'s
  nullable FK columns. Also has only a response-SLA row (still in
  progress), no resolution row yet.
- `case-0007` — reproduces the real "Unknown Agent" bug this project
  found and fixed: `assigned_to_name` (and 3 other role names) equal the
  raw sys_id itself, and no matching `sys_user` row exists either —
  exactly the ServiceNow data-quality gap documented in CLAUDE.md. Proves
  `dim_agent.sql`'s `'Unknown Agent (' || right(sys_id, 6) || ')'`
  fallback still fires correctly.
- `case-0008` — no parking terminal at all — exercises `dim_terminal`'s
  `where parking_terminal_sys_id is not null` filter and `fact_case`'s
  nullable terminal FK.

`sys_user.csv` deliberately has no row for the case-0007 agent (that's
the point being tested) and no row for a "genuinely no sys_user record"
scenario beyond that.

`contract_sla.csv` has exactly the 2 SLA definitions the gold layer
actually filters on (`vars.response_sla_name` /
`vars.resolution_sla_name` in `dbt_project.yml`) — anything else would
never be selected by `fact_case.sql`'s `sla_pivot` CTE.
