Project layout (canonical)

- etl/                              # Canonical application package
  - __init__.py
  - client.py                       # API client + retries + rate-limit
  - extractors/
    - servicenow.py                 # Source extraction logic
  - loaders/
    - postgres.py                   # Staging + bronze loaders
    - extraction_state.py           # Watermarks + run metadata
  - pipelines/
    - load_bronze_raw.py            # Bronze pipeline orchestration

- dags/                             # Airflow DAG definitions
- exploration/                      # Ad-hoc scripts only (non-production)
- data/                             # Local snapshots/samples

How to run (quick test)

1) Ensure .env contains SN_BASE_URL, SN_USERNAME, SN_PASSWORD, SN_ACCOUNT_QUERY, ELT_DATABASE_* etc.

2) Start Docker stack:

```bash
docker compose up -d
```

3) Run a quick API check (uses `etl.client`):

```bash
docker compose run --rm -v C:\pfe\sn_analytics:/opt/airflow -w /opt/airflow airflow-cli \
  python -c "from etl.client import ServiceNowClient; c=ServiceNowClient(); print('count', c.count_records('sn_customerservice_case'))"
```

4) Run the production pipeline (incremental using SN_ACCOUNT_QUERY by default):

```bash
docker compose run --rm -v C:\pfe\sn_analytics:/opt/airflow -w /opt/airflow airflow-cli \
  python -m etl.pipelines.load_bronze_raw --table sn_customerservice_case --batch-size 500 --incremental
```

Notes
- Production code should use only `etl.*` imports.
- Legacy wrapper folders were removed to keep a single consistent structure.
