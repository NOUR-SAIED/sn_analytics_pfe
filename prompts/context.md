# Project Context — ServiceNow Analytics ELT

## Overview
This project implements an ELT pipeline to extract data from ServiceNow, load it into PostgreSQL, and transform it into analytics-ready models. It is orchestrated with Apache Airflow (CeleryExecutor, Redis, Postgres) and designed for modularity, scalability, and reuse.

## Architecture
The pipeline follows a layered data model:

- **Bronze Layer**
  - Raw ingestion from ServiceNow API
  - Data stored as JSONB in PostgreSQL
  - No transformations applied

- **Silver Layer**
  - Flattened and standardized incident dataset
  - Code/label normalization (e.g. priority, state, category)
  - Computed operational metrics (response time, resolution time, assignment lag, closure lag)
  - Acts as the core analytical foundation for downstream models

- **Gold Layer**
  - Aggregated KPI tables for BI and dashboards
  - SLA metrics, lifecycle analytics, backlog trends
  - Optimized for Superset consumption

## Core Components

### etl_core/
- `api/config.py`: API configuration (auth, retries, rate limits, batch size)
- `api/servicenow_api.py`: ServiceNow API client (pagination, resilience, authentication)
- `loaders/postgres_jsonb.py`: Raw JSONB ingestion into PostgreSQL

### dags/
- `sn_account_bronze_extract.py`: Bronze ingestion DAG (ServiceNow → PostgreSQL)
- `etl_core_tasks.py`: Shared extraction and load tasks
- Test DAGs for validation (`test_extraction.py`, `test_e2e_load.py`, `test_dag.py`)

### docker-compose.yml
- Airflow (scheduler, workers, webserver)
- Redis (Celery broker)
- PostgreSQL (metadata + ELT storage)

### exploration/
- Schema inspection scripts
- KPI exploration and field analysis
- Data profiling utilities

## Silver Layer Design Principles

- All categorical fields are split into:
  - `*_code` (raw system value)
  - `*_label` (human readable value)

- Time fields are normalized into:
  - Duration in seconds (BIGINT)

- Core computed metrics:
  - Response time
  - Resolution time
  - Assignment delay
  - Closure lag

- Silver layer is split into:
  - Wide normalized incident table (base)
  - Future domain tables (cases, users, assignments)

## ELT Flow Summary

1. Extract data from ServiceNow API (filtered by account)
2. Store raw records in PostgreSQL JSONB (Bronze)
3. Flatten and normalize into Silver incidents table
4. Build domain-specific Silver tables (future step)
5. Aggregate into Gold KPI marts for dashboards

## Key Design Features

- Modular ETL core package (`etl_core`)
- Config-driven pipeline using environment variables
- Resilient API layer (retry, backoff, pagination)
- Airflow orchestration in Dockerized environment
- Strict separation between Bronze, Silver, Gold
- Silver layer serves as both normalization and analytical staging layer