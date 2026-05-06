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
        print(f"ServiceNow API Config:")
        print(f"  Base URL: {cls.BASE_URL}")
        print(f"  Username: {cls.USERNAME}")
        print(f"  Account Query: {cls.ACCOUNT_QUERY}")
        print(f"  Table: {cls.TABLE_NAME}")
        print(f"  Batch Size: {cls.BATCH_SIZE}")
        print(f"  Timeout: {cls.TIMEOUT_SEC}s")
        print(f"  Max Retries: {cls.MAX_RETRIES}")
        print(f"  Rate Limit: {cls.MAX_REQUESTS_PER_SEC} req/sec")
