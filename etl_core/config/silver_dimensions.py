"""
Dimension/lookup table configurations for silver layer.

These tables are derived from silver.incidents_flat.
They normalize repeated entity references so incidents only
stores the FK sys_id, not denormalized name/label.

Tables:
    silver.users           — agents/assignees from incident fields
    silver.assignment_groups — support teams from assignment_group
    silver.terminals       — parking terminals from device fields

Expand with more tables/fields ONLY when source ServiceNow data is available.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SilverDimensionConfig:
    """
    Configuration for a silver dimension/lookup table.
    These tables are populated by deduplicating entities from existing
    silver fact tables rather than extracted directly from bronze.
    """

    target_schema: str = "silver"
    target_table: str = ""
    source_silver_table: str = "incidents"
    source_sys_id_field: str = ""
    source_name_fields: List[str] = field(default_factory=list)
    extract_mode: str = "all_unique"
    notes: str = ""

    def __post_init__(self):
        if not self.target_table:
            raise ValueError("target_table must be set")


USERS = SilverDimensionConfig(
    target_table="users",
    source_silver_table="incidents_flat",
    source_sys_id_field="assigned_to_sys_id",
    source_name_fields=["assigned_to_name", "resolved_by_name", "last_assignee_name", "opened_by_name", "owned_by_name"],
    notes="Agents referenced in incidents.",
)

ASSIGNMENT_GROUPS = SilverDimensionConfig(
    target_table="assignment_groups",
    source_silver_table="incidents_flat",
    source_sys_id_field="assignment_group_sys_id",
    source_name_fields=["assignment_group_name"],
    notes="Support/assignment teams.",
)

TERMINALS = SilverDimensionConfig(
    target_table="terminals",
    source_silver_table="incidents_flat",
    source_sys_id_field="parking_terminal_sys_id",
    source_name_fields=["parking_terminal_name", "device_number"],
    notes="Parking terminal/device entities.",
)


DIM_REGISTRY: dict[str, SilverDimensionConfig] = {
    "users": USERS,
    "assignment_groups": ASSIGNMENT_GROUPS,
    "terminals": TERMINALS,
}


def get_dimension_config(table_name: str) -> SilverDimensionConfig:
    config = DIM_REGISTRY.get(table_name)
    if not config:
        raise KeyError(
            f"No dimension config registered for '{table_name}'. "
            f"Available: {list(DIM_REGISTRY.keys())}"
        )
    return config


def register_dimension(config: SilverDimensionConfig) -> None:
    DIM_REGISTRY[config.target_table] = config