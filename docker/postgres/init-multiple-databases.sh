#!/bin/bash

set -e
set -u

function create_user_and_database() {
    local database=$1
    local username=$2
    local password=$3
    echo "Creating user '$username' and database '$database'"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
        CREATE USER $username WITH PASSWORD '$password';
        CREATE DATABASE $database;
        GRANT ALL PRIVILEGES ON DATABASE $database TO $username;
EOSQL
    echo "  User '$username' and database '$database' created successfully"
}

function create_readonly_db_login() {
    # Creates a login with CONNECT-only access to an existing database.
    # Schema/table-level SELECT grants are applied separately once the
    # target schema exists (see etl_core.gold.loader.grant_copilot_reader_access,
    # called from the gold_build DAG on every run) since it doesn't exist yet
    # on a fresh init.
    local database=$1
    local username=$2
    local password=$3
    echo "Creating read-only login '$username' for database '$database'"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
        CREATE USER $username WITH PASSWORD '$password';
        GRANT CONNECT ON DATABASE $database TO $username;
EOSQL
    echo "  Login '$username' created successfully"
}

# Metadata database
create_user_and_database $METADATA_DATABASE_NAME $METADATA_DATABASE_USERNAME $METADATA_DATABASE_PASSWORD

# Celery result backend database
create_user_and_database $CELERY_BACKEND_NAME $CELERY_BACKEND_USERNAME $CELERY_BACKEND_PASSWORD

# ELT database
create_user_and_database $ELT_DATABASE_NAME $ELT_DATABASE_USERNAME $ELT_DATABASE_PASSWORD

# Copilot (text-to-SQL agent) read-only login, scoped to the gold schema in elt_sn_db
create_readonly_db_login $ELT_DATABASE_NAME $COPILOT_DB_USERNAME $COPILOT_DB_PASSWORD

#superset database
create_user_and_database $SUPERSET_DATABASE_NAME $SUPERSET_DATABASE_USERNAME $SUPERSET_DATABASE_PASSWORD

echo "All databases and users created successfully"