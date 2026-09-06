"""
Simple ServiceNow API client.
Fetches records from a specific table, filtered by account query.
No complex state tracking - just extraction.
"""

import time
from typing import Dict, List, Any, Optional
import requests
from requests.auth import HTTPBasicAuth

from etl_core.api.config import APIConfig


class ServiceNowAPIClient:
    """
    Simple, focused API client for ServiceNow table extraction.
    
    Responsibilities:
    - Make authenticated API calls
    - Handle retries and rate limiting
    - Yield paginated results
    - Apply account filtering
    """

    def __init__(self, config: APIConfig = None):
        self.config = config or APIConfig()
        self.config.validate()
        self.session = self._create_session()
        self.last_request_time = 0.0

    def _create_session(self) -> requests.Session:
        """Create authenticated session."""
        session = requests.Session()
        session.auth = HTTPBasicAuth(self.config.USERNAME, self.config.PASSWORD)
        session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "ELT-Pipeline/1.0"
        })
        return session

    def _rate_limit_wait(self) -> None:
        """Enforce rate limiting: max N requests per second."""
        min_interval = 1.0 / self.config.MAX_REQUESTS_PER_SEC
        elapsed = time.time() - self.last_request_time
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self.last_request_time = time.time()

    def _fetch_page(
        self,
        table: str,
        query: str,
        limit: int,
        offset: int,
        fields: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch a single page from the API with retries.
        
        Args:
            table: ServiceNow table name
            query: sysparm_query filter string
            limit: Number of records per page
            offset: Starting position
            fields: Comma-separated list of fields to return (sysparm_fields)
            
        Returns:
            List of records from this page
            
        Raises:
            Exception if all retries exhausted
        """
        url = f"{self.config.BASE_URL}/api/now/table/{table}"
        params = {
            "sysparm_query": query,
            "sysparm_limit": limit,
            "sysparm_offset": offset,
            "sysparm_display_value": "all"
        }
        
        if fields:
            params["sysparm_fields"] = fields

        for attempt in range(self.config.MAX_RETRIES + 1):
            self._rate_limit_wait()

            try:
                response = self.session.get(
                    url,
                    params=params,
                    timeout=self.config.TIMEOUT_SEC
                )

                # Rate limit / server errors: retry with backoff
                if response.status_code in (429, 502, 503, 504):
                    if attempt < self.config.MAX_RETRIES:
                        wait_time = 2 ** attempt
                        print(f"  [Attempt {attempt + 1}] HTTP {response.status_code}. Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception(
                            f"Max retries exceeded. Last HTTP status: {response.status_code}"
                        )

                # Other client/server errors: fail immediately
                if response.status_code >= 400:
                    raise Exception(
                        f"API request failed (HTTP {response.status_code}): {response.text[:200]}"
                    )

                # Success
                data = response.json()
                return data.get("result", [])

            except requests.exceptions.Timeout:
                if attempt < self.config.MAX_RETRIES:
                    wait_time = 2 ** attempt
                    print(f"  [Attempt {attempt + 1}] Timeout. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"Request timeout after {self.config.MAX_RETRIES} retries")

            except requests.exceptions.ConnectionError as e:
                if attempt < self.config.MAX_RETRIES:
                    wait_time = 2 ** attempt
                    print(f"  [Attempt {attempt + 1}] Connection error. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"Connection failed after {self.config.MAX_RETRIES} retries: {e}")

    def fetch_all_records(
        self,
        table: str,
        query_filter: Optional[str] = None,
        fields: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch all records from a table, filtered by account.
        
        Args:
            table: ServiceNow table name
            query_filter: Specific query string for the table (e.g. account=123)
            fields: Optional comma-separated list of fields to return
            
        Returns:
            List of all records matching the query
        """
        query = query_filter or self.config.ACCOUNT_QUERY
        if not query:
            raise ValueError(f"No query filter provided for table '{table}'. Subsidiary filtering is strictly required.")

        all_records: List[Dict[str, Any]] = []
        offset = 0

        print(f"\n[EXTRACT] Fetching records from table '{table}'")
        print(f"   Query filter: {query}")
        if fields:
            print(f"   Fields: {fields}")
        print(f"   Batch size: {self.config.BATCH_SIZE}")
        print("-" * 60)

        while True:
            print(f"   Fetching offset={offset}...", end=" ")
            
            batch = self._fetch_page(
                table=table,
                query=query,
                limit=self.config.BATCH_SIZE,
                offset=offset,
                fields=fields
            )

            if not batch:
                print("(empty)")
                break

            print(f"({len(batch)} records)")
            all_records.extend(batch)

            # If we got fewer than batch_size, we've reached the end
            if len(batch) < self.config.BATCH_SIZE:
                break

            offset += self.config.BATCH_SIZE

        print("-" * 60)
        print(f"[SUCCESS] Total records fetched: {len(all_records)}\n")
        return all_records
