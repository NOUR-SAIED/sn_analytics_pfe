# Silver Incidents Table — Data Dictionary

> **Source table:** `sn_customerservice_case`  
> **Total columns:** ~85  
> **Primary Key:** `bronze_id` (NOT NULL) + `sys_id` (natural key)

---

## Summary

| Category | Detail |
|---|---|
| **Total columns** | ~85 |
| **Primary Key** | `bronze_id` (NOT NULL), `sys_id` (natural) |
| **Nullable risk** | Most FK fields, all timestamps, all coded fields |
| **High-risk nullable** | `extraction_run_id`, `opened_at`, `assigned_at`, `first_response_time` |
| **FK reference tables** | `sys_user`, `sys_user_group`, `core_company` (confirmed) |
| **Ambiguous / needs validation** | `task_effective_number`, `u_sub_category`, `case_evaluation_sys_id`, `account_sys_id` vs `company_sys_id` redundancy |

---

## Domain: Identity (Primary Key)

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `bronze_id` | TEXT | **NOT NULL** | FK to `raw_incidents.id` (bronze primary key) |
| `source_table` | TEXT | NOT NULL | Always `sn_customerservice_case` |
| `extraction_run_id` | TEXT | NULL | Airflow run ID — nullable in initial loads |
| `sys_id` | TEXT | NOT NULL | ServiceNow system ID — natural PK, unique per record |
| `case_number` | TEXT | NULL | Human-readable incident number (e.g., `INC0010234`) |

---

## Domain: Classification

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `case_title` | TEXT | NULL | Case short description |
| `sys_class_name` | TEXT | NULL | ServiceNow table class (e.g., `sn_customerservice_case`) |
| `task_effective_number` | TEXT | NULL | ⚠️ Conflicting docs — see open question below |

> **❓ Open question about `task_effective_number`:** This file previously marked it fully unknown.
> `docs/data_dictionary.md` describes it more confidently as *"Same as `number` in most cases. Used
> when case is linked to a parent task"* (100% populated, cardinality 10 in that sample). The two docs
> haven't been reconciled against each other or confirmed with a stakeholder — until someone verifies
> the `data_dictionary.md` description against real parent/child case behavior, treat it as unresolved
> rather than trusting either doc alone.

---

## Domain: Lifecycle & State

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `state_code` | INTEGER | NULL | Numeric state (1=New, 2=Active, etc.) |
| `state_label` | TEXT | NULL | Human-readable state |
| `active` | BOOLEAN | NULL | True if case is open |
| `auto_close` | BOOLEAN | NULL | True if case auto-closed by system |
| `escalation_code` | TEXT | NULL | Escalation level code |
| `escalation_label` | TEXT | NULL | Escalation level label |

---

## Domain: Priority / Severity

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `priority_code` | INTEGER | NULL | 1=Critical, 2=High, 3=Medium, 4=Low (SN default) |
| `priority_label` | TEXT | NULL | Display label |
| `urgency_code` | INTEGER | NULL | Impact/urgency scale |
| `urgency_label` | TEXT | NULL | Display label |
| `impact_code` | INTEGER | NULL | Business impact scale |
| `impact_label` | TEXT | NULL | Display label |

---

## Domain: Category & Assignment

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `category_code` | TEXT | NULL | Top-level category code |
| `category_label` | TEXT | NULL | Display label: Corrective Maintenance, Preventive Maintenance, Service Request,Installation |
| `subcategory_code` | TEXT | NULL | Sub-category code |
| `subcategory_label` | TEXT | NULL | Display label |
| `u_sub_category` | TEXT | NULL | where it was resolved(onsite, remote) |
| `contact_type` | TEXT | NULL | How case was opened (phone, email, portal...) |

---

## Domain: Resolution

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `resolution_code` | TEXT | NULL | Resolution category code |
| `resolution_code_label` | TEXT | NULL | Display label:  the type of the problem level (software, hardware, non system bug) |
| `sub_code` | TEXT | NULL | Sub-resolution code |
| `sub_code_label` | TEXT | NULL | Display label: category of the incident(database level, payment lbl, defect config) |
| `cause` | TEXT | NULL | Root cause description |
| `close_notes` | TEXT | NULL | Closure notes text |

---

## Domain: SLA

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `made_sla` | BOOLEAN | NULL | True if SLA was met |
| `u_sla_breached` | BOOLEAN | NULL | Custom flag — breached |
| `sla_due` | TIMESTAMPTZ | NULL | SLA deadline timestamp |

> **ℹ️ Note:** Calendar-time durations from timestamps are in `response_time_s`, `resolution_time_s`.
> Business-hours SLA is joined at the gold layer, not here: `gold.fact_case`'s `sla_pivot` CTE
> (`etl_core/gold/fact_case.py`) pivots `silver.task_sla` joined to `silver.contract_sla` on
> `sla_sys_id`, filtered to the two named SLA definitions in `etl_core/gold/config.py`
> (`RESPONSE_SLA_NAME = "TPA first reaction SLA"`, `RESOLUTION_SLA_NAME = "TPA case resolution SLA"`),
> reshaped into one row per case before joining into the fact table. This avoids join fan-out — without
> the pivot, cases with both SLA types would double-count in every downstream `COUNT`/`SUM`. *(This
> note previously said "not yet joined" — that was stale; the join has existed since the gold star
> schema was built.)*

---

## Domain: Timestamps

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `opened_at` | TIMESTAMPTZ | NULL | Case opened timestamp |
| `closed_at` | TIMESTAMPTZ | NULL | Case closed timestamp |
| `resolved_at` | TIMESTAMPTZ | NULL | Case resolved timestamp |
| `assigned_at` | TIMESTAMPTZ | NULL | First assignment timestamp |
| `first_response_time` | TIMESTAMPTZ | NULL | First response to customer |
| `sys_created_on` | TIMESTAMPTZ | NULL | Record creation in SN |
| `sys_updated_on` | TIMESTAMPTZ | NULL | Record last update in SN |
| `u_date_of_occurrence` | DATE | NULL | Custom date — incident occurrence date |

---

## Domain: SLA Computed Metrics (Derived)

| Column | Type | Nullable | Formula |
|---|---|---|---|
| `response_time_s` | BIGINT | NULL | `first_response_time - opened_at` (seconds) |
| `resolution_time_s` | BIGINT | NULL | `resolved_at - opened_at` (seconds) |
| `assign_time_s` | BIGINT | NULL | `assigned_at - opened_at` (seconds) |
| `closure_lag_s` | BIGINT | NULL | `closed_at - resolved_at` (seconds) |

---

## Domain: Assignment (FK References)

| Column | Type | Nullable | FK Target | Notes |
|---|---|---|---|---|
| `assigned_to_sys_id` | TEXT | NULL | `sys_user.sys_id` | Current assigned agent |
| `opened_by_sys_id` | TEXT | NULL | `sys_user.sys_id` | Creator |
| `resolved_by_sys_id` | TEXT | NULL | `sys_user.sys_id` | Resolver |
| `owned_by_sys_id` | TEXT | NULL | `sys_user.sys_id` | Case owner |
| `last_assignee_sys_id` | TEXT | NULL | `sys_user.sys_id` | Last assignee |
| `contact_sys_id` | TEXT | NULL | `sys_user.sys_id` | Customer contact |
| `assignment_group_sys_id` | TEXT | NULL | `sys_user_group.sys_id` | Team assigned |
| `last_assignment_group_sys_id` | TEXT | NULL | `sys_user_group.sys_id` | Last team |

---

## Domain: Account (FK References)

| Column | Type | Nullable | FK Target | Notes |
|---|---|---|---|---|
| `account_sys_id` | TEXT | NULL | `core_company.sys_id` | Account reference |
| `company_sys_id` | TEXT | NULL | `core_company.sys_id` | Company reference |

> **❓ Open question:** Are `account` and `company` the same entity in ServiceNow setup? They both point to `core_company`. If redundant, which is authoritative? 

---

## Domain: Device / Terminal (Custom FK)

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `parking_terminal_sys_id` | TEXT | NULL | Terminal/parking device reference |
| `device_number` | TEXT | NULL | Device identifier string |
| `device_type_code` | TEXT | NULL | Device type code |
| `device_type_label` | TEXT | NULL | Display label |
| `fault_category_code` | TEXT | NULL | Fault category code |
| `fault_category_label` | TEXT | NULL | Display label |

---

## Domain: Business Impact (Custom Coded)

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `financial_impact_code` | TEXT | NULL | Financial impact level code |
| `financial_impact_label` | TEXT | NULL | Display label |
| `operational_impact_code` | TEXT | NULL | Operational impact level code |
| `operational_impact_label` | TEXT | NULL | Display label |

---

## Domain: Workflow / Service (Custom FK)

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `service_window_sys_id` | TEXT | NULL | Service window reference — SLA window? |
| `case_evaluation_sys_id` | TEXT | NULL | ⚠️ Needs stakeholder clarification |

> **❓ Open question about `case_evaluation_sys_id`:** What is this reference table? A checklist, audit, or scoring table?

---

## Domain: Flags / Booleans

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `knowledge` | BOOLEAN | NULL | Linked to knowledge base article |
| `proactive` | BOOLEAN | NULL | Proactive case flag |
| `needs_attention` | BOOLEAN | NULL | Needs attention flag |
| `has_best_practice` | BOOLEAN | NULL | Best practice article used |
| `has_incident` | BOOLEAN | NULL | Linked incident exists |
| `quality_check_done` | BOOLEAN | NULL | Quality check completed |

---

## Domain: Metadata / Audit

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `sys_created_by` | TEXT | NULL | ServiceNow username who created |
| `sys_updated_by` | TEXT | NULL | Last modifier username |
| `reassignment_count` | BIGINT | NULL | Number of reassignments |
| `sys_mod_count` | BIGINT | NULL | Number of modifications |
| `case_report_sys_id` | TEXT | NULL | Case report reference |

---

## Domain: Approval

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `approval_code` | TEXT | NULL | Approval status code |
| `approval_label` | TEXT | NULL | Display label |
| `notify_code` | TEXT | NULL | Notification preference code |
| `notify_label` | TEXT | NULL | Display label |

---

*Last updated: 2026-05-18*