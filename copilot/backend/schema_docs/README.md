# Gold Schema Docs

Use these notes as the first stop when reasoning over the gold layer.

## Start here
- Read `fact_case.md` first for the main case grain and all fact-level fields.
- Then use the dimension docs for label lookups and grouping.

## Table map
- `dim_date.md`: calendar lookup for all date keys.
- `dim_agent.md`: people and assignee lookup.
- `dim_assignment_group.md`: team and routing lookup.
- `dim_terminal.md`: parking terminal lookup.
- `fact_case.md`: one row per customer service case.

## Agent guidance
- Join facts to dimensions instead of reusing raw labels from the source when possible.
- Use `fact_case` for case-level analysis, then expand with the relevant dimension doc.
- Treat `loaded_at` as warehouse load time, not business time.
