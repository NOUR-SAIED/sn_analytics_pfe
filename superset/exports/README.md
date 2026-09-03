# Superset dashboard export

Version-controlled snapshot of the "Cases Analytics" dashboard (id 3 in the running instance) —
the dashboard layout, all 28 charts, all 5 datasets, and the 2 database connections (PostgreSQL,
Cube), as human-readable YAML instead of living only in Superset's metadata database.

This closes a gap that was open for most of this project: Superset assets (dashboards, charts,
datasets) were previously not tracked anywhere outside the running container — if that Postgres
metadata DB were ever lost or reset, all of it (this whole redesign included) would be gone
with no way to recover it. Now it's just files, reviewable in a diff like any other code change.

## What's in here

```
cases_analytics_dashboard/
  dashboards/Cases_Analytics_3.yaml       # layout, filters, theme, custom CSS
  charts/*.yaml                            # one file per chart (viz type, query, formatting)
  datasets/**/*.yaml                       # dataset definitions (ds_cases_main, the Cube "Cases" cube, etc.)
  databases/*.yaml                         # connection metadata (passwords masked as XXXXXXXXXX,
                                            # never exported — re-enter them on import)
  metadata.yaml                            # export manifest
```

## Re-generating this export

After making changes in Superset's UI (or via its API), regenerate with:

```bash
curl -s -c /tmp/ss_cookies.txt -X POST http://localhost:8088/api/v1/security/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin1234","provider":"db","refresh":true}' \
  -o /tmp/ss_login.json

TOKEN=$(python -c "import json; print(json.load(open('/tmp/ss_login.json'))['access_token'])")

curl -s -b /tmp/ss_cookies.txt -H "Authorization: Bearer $TOKEN" \
  -o dashboard_export.zip "http://localhost:8088/api/v1/dashboard/export/?q=!(3)"

unzip -o dashboard_export.zip -d cases_analytics_dashboard_new
# then diff cases_analytics_dashboard_new against cases_analytics_dashboard/ and replace if it looks right
```

## Restoring into a fresh Superset instance

Superset → Settings → Import Dashboards, or via API:
`POST /api/v1/dashboard/import/` with the re-zipped folder. You'll be prompted to re-enter the
database passwords (they're intentionally not in the export).

## Known limitation

This is a manual, point-in-time snapshot — not wired into CI (there isn't one yet) to
regenerate automatically on every dashboard change. Re-run the export above after
significant dashboard work and commit the diff.
