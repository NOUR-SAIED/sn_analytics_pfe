import sys
from dotenv import load_dotenv
load_dotenv('C:\\pfe\\sn_analytics\\.env')
import os

sys.path.append('C:\\pfe\\sn_analytics')
from etl_core.loaders.postgres_jsonb import PostgresJSONBLoader

loader = PostgresJSONBLoader(host="localhost", database="elt_sn_db", user="elt_user", password="1234", port=5432)
print("Records in raw_sys_user:", loader.get_record_count("raw_sys_user"))
