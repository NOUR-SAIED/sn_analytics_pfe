import sys
from dotenv import load_dotenv
import os
import psycopg2

load_dotenv('C:\\pfe\\sn_analytics\\.env')
sys.path.append('C:\\pfe\\sn_analytics')

# Fetch connection details from .env
DB_HOST = "localhost" # Assuming port-forwarded or running locally
DB_PORT = os.getenv("POSTGRES_CONN_PORT", "5432")
DB_NAME = os.getenv("ELT_DATABASE_NAME")
DB_USER = os.getenv("ELT_DATABASE_USERNAME", "elt_user")
DB_PASS = os.getenv("ELT_DATABASE_PASSWORD")

try:
    conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS)
    conn.autocommit = True
    cur = conn.cursor()

    legacy_tables = [
        "silver.incidents_flat",
        "silver.incidents",
        "silver.users",
        "silver.assignment_groups",
        "silver.terminals"
    ]

    print("Dropping legacy silver tables...")
    for table in legacy_tables:
        print(f"  Dropping {table}...", end=" ")
        try:
            cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
            print("Done.")
        except Exception as e:
            print(f"Failed: {e}")

    cur.close()
    conn.close()
    print("\nCleanup complete!")

except Exception as e:
    print(f"Connection failed: {e}")
