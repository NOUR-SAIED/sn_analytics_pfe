"""
API Configuration for ServiceNow extraction.
Centralized settings for credentials, timeouts, retries.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class APIConfig:
    """ServiceNow API configuration from environment."""

    # Credentials
    BASE_URL = os.getenv("SN_BASE_URL", "https://scbmtest.service-now.com")
    USERNAME = os.getenv("SN_USERNAME")
    PASSWORD = os.getenv("SN_PASSWORD")

    # Query filter (account-specific)
    ACCOUNT_QUERY = os.getenv("SN_ACCOUNT_QUERY", "")

    # Config for all tables to extract, enforcing the subsidiary filter
    TABLES_CONFIG = {
        "sn_customerservice_case": {
            "bronze_table": "raw_incidents",
            "query_filter": os.getenv("SN_ACCOUNT_QUERY", "")
        },
        "task_sla": {
            "bronze_table": "raw_task_sla",
            "query_filter": os.getenv("SN_TASK_SLA_QUERY", "sla=6e4aa021c36c6e50021caddc7a0131b1^ORsla=fefbe26fc38322d0021caddc7a0131d5")
        },
        "sys_user": {
            "bronze_table": "raw_sys_user",
            "query_filter": os.getenv("SN_SYS_USER_QUERY", "company=4bcd89671b557f4063c43113dd4bcb10"),
            "fields": "sys_id,name,u_personal_id,user_name,u_stockroom,mobile_phone,first_name,email,last_name,sys_updated_on"
        },
        "contract_sla": {
            "bronze_table": "raw_contract_sla",
            "query_filter": os.getenv("SN_CONTRACT_SLA_QUERY", "nameLIKEtpa")
        }
    }

    # API behavior
    TIMEOUT_SEC = int(os.getenv("SN_TIMEOUT_SEC", "30"))
    MAX_RETRIES = int(os.getenv("SN_MAX_RETRIES", "3"))
    BATCH_SIZE = int(os.getenv("SN_BATCH_SIZE", "100"))
    MAX_REQUESTS_PER_SEC = float(os.getenv("SN_MAX_REQUESTS_PER_SEC", "5.0"))

    # Defaults
    TABLE_NAME = "sn_customerservice_case"

    @classmethod
    def validate(cls) -> None:
        """Ensure required credentials are set."""
        if not all([cls.BASE_URL, cls.USERNAME, cls.PASSWORD]):
            raise ValueError(
                "Missing required env vars: SN_BASE_URL, SN_USERNAME, SN_PASSWORD"
            )
        if not cls.ACCOUNT_QUERY:
            raise ValueError(
                "Missing SN_ACCOUNT_QUERY env var (account-specific filter)"
            )

    @classmethod
    def log_config(cls) -> None:
        """Log configuration (masking sensitive values)."""
        print("ServiceNow API Config:")
        print(f"  Base URL: {cls.BASE_URL}")
        print(f"  Username: {cls.USERNAME}")
        print(f"  Account Query: {cls.ACCOUNT_QUERY}")
        print(f"  Table: {cls.TABLE_NAME}")
        print(f"  Batch Size: {cls.BATCH_SIZE}")
        print(f"  Timeout: {cls.TIMEOUT_SEC}s")
        print(f"  Max Retries: {cls.MAX_RETRIES}")
        print(f"  Rate Limit: {cls.MAX_REQUESTS_PER_SEC} req/sec")
