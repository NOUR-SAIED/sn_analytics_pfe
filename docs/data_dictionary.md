# Data Dictionary — sn_customerservice_case

Generated from: `sn_data_2026-05-02.json`  
Records analyzed: **10**  
Total fields: **233** | Non-empty: **127** | Always empty: **106**

Excluded EMPTY fields: **106** — these are always empty in the snapshot and omitted from sections.

## FK Tables Detected

- **`cmn_schedule`** ← `u_service_window`
- **`core_company`** ← `company`
- **`customer_account`** ← `account`, `u_tpl`
- **`customer_contact`** ← `contact`
- **`sn_customerservice_case_report`** ← `case_report`
- **`sys_user`** ← `assigned_to`, `opened_by`, `resolved_by`, `u_last_assignee`, `u_owned_by`
- **`sys_user_group`** ← `assignment_group`, `sys_domain`, `u_last_assignment_group`
- **`u_case_evaluation`** ← `u_case_evaluation`

---

## Identity

| Field | Type | Fill | FK Table | Sample Value | All Values / Notes | Business Meaning |
|---|---|---|---|---|---|---|
| `number` | TEXT | 100% | — | `CS0395813` | cardinality: 10 | **Case Number** — Human-readable case ID shown to customers. e.g. CS0395813 |
| `sys_id` | TEXT | 100% | — | `287402c23b706ed091e0703a85e45acb` | cardinality: 10 | **System ID** — Internal 32-char UUID. Primary key for joins. Never shown in reports. |
| `task_effective_number` | TEXT | 100% | — | `CS0395813` | cardinality: 10 | **Effective Number** — Same as number in most cases. Used when case is linked to a parent task. |
| `case` | TEXT | 100% | — | `TEST​CS0395813` | cardinality: 10 | **Case Title** — Concatenation of prefix and number. UI display field. |
| `sys_class_name` | CHOICE | 100% | — | `sn_customerservice_case` → `Case` | `sn_customerservice_case`→`Case` | **Record Type** — Always 'sn_customerservice_case'. Confirms table type. |

## Lifecycle & Status

| Field | Type | Fill | FK Table | Sample Value | All Values / Notes | Business Meaning |
|---|---|---|---|---|---|---|
| `state` | CHOICE | 100% | — | `3` → `Closed` | `3`→`Closed` | **Case State** — Lifecycle stage. e.g. Open, In Progress, Closed, Resolved. |
| `active` | BOOLEAN | 100% | — | `false` | `false` | **Is Active** — true = case is open. false = closed or resolved. |
| `auto_close` | BOOLEAN | 100% | — | `true` | `false`, `true` | **Auto Close Flag** — true = case was closed automatically by the system, not by an agent. |
| `stage` | EMPTY | 100% | — | `` | cardinality: 0 | **Stage** — More granular lifecycle stage within a state. |
| `escalation` | CHOICE | 100% | — | `0` → `Normal` | `0`→`Normal` | **Escalation Level** — Whether the case has been escalated. Normal = not escalated. |

## Priority & Severity

| Field | Type | Fill | FK Table | Sample Value | All Values / Notes | Business Meaning |
|---|---|---|---|---|---|---|
| `priority` | CHOICE | 100% | — | `4` → `4 - Low` | `2`→`2 - High` / `3`→`3 - Moderate` / `4`→`4 - Low` | **Priority** — Combined urgency + impact. 1=Critical, 2=High, 3=Medium, 4=Low. |
| `urgency` | CHOICE | 100% | — | `3` → `3 - Low` | `1`→`1 - High` / `2`→`2 - Medium` / `3`→`3 - Low` | **Urgency** — How quickly customer needs resolution. Input to priority calculation. |
| `impact` | CHOICE | 100% | — | `3` → `3 - Low` | `2`→`2 - Medium` / `3`→`3 - Low` | **Impact** — Business impact of the issue. Input to priority calculation. |

## Classification

| Field | Type | Fill | FK Table | Sample Value | All Values / Notes | Business Meaning |
|---|---|---|---|---|---|---|
| `category` | CHOICE | 100% | — | `1001` → `Corrective Maintenance` | `1001`→`Corrective Maintenance` / `1002`→`Service Request` | **Category** — Top-level case type. e.g. Corrective Maintenance. |
| `subcategory` | CHOICE | 100% | — | `0` → `Question` | `0`→`Question` | **Subcategory** — Second-level type under category. |
| `u_sub_category` | TEXT | 100% | — | `Remote` → `entervo.it.security` | cardinality: 3 | **Custom Subcategory** — TPA-specific. Remote = resolved without site visit. Onsite = field visit required. |
| `contact_type` | TEXT | 100% | — | `Portal` | cardinality: 1 | **Channel** — How the case was submitted. e.g. Portal, Email, Phone. |

## Resolution

| Field | Type | Fill | FK Table | Sample Value | All Values / Notes | Business Meaning |
|---|---|---|---|---|---|---|
| `resolution_code` | CHOICE | 100% | — | `non_system_bug` → `Non System Bug` | `10`→`Hardware` / `non_system_bug`→`Non System Bug` / `software`→`Software` | **Resolution Code** — How the case was resolved. e.g. Non System Bug, Configuration Change. |
| `u_sub_code` | CHOICE | 100% | — | `no_fault_found` → `No Fault Found` | `cancelled_by_customer`→`Cancelled by customer` / `configuration`→`Configuration` / `customer_request`→`Customer Request` / `no_fault_found`→`No Fault Found` / `user_error`→`User Error` / `wear_and_tear`→`Wear and Tear` | **Resolution Sub-Code** — TPA-specific drill-down on resolution. e.g. No Fault Found, Software Fix. |
| `cause` | TEXT | 100% | — | `Test` | cardinality: 10 | **Cause** — Root cause description entered by agent at close. |
| `close_notes` | TEXT | 100% | — | `Test` | cardinality: 10 | **Close Notes** — Agent notes written at case closure. |

## SLA

| Field | Type | Fill | FK Table | Sample Value | All Values / Notes | Business Meaning |
|---|---|---|---|---|---|---|
| `made_sla` | BOOLEAN | 100% | — | `true` | `true` | **Made SLA** — Standard SN SLA met flag. |
| `u_sla_breached` | BOOLEAN | 100% | — | `false` | `false`, `true` | **SLA Breached** — TPA custom SLA breach tracking flag. |
| `sla_due` | EMPTY | 100% | — | `` → `UNKNOWN` | cardinality: 0 | **SLA Deadline** — Datetime by which case must be resolved per SLA contract. |

## People

| Field | Type | Fill | FK Table | Sample Value | All Values / Notes | Business Meaning |
|---|---|---|---|---|---|---|
| `assigned_to` | FK_REF | 100% | `sys_user` | `Denis Kerrutt` | `Denis Kerrutt` | **Assigned Agent** — Support agent currently responsible. FK → sys_user. |
| `opened_by` | FK_REF | 80% | `sys_user` | `03d0b4203b00ae9091e0703a85e45a45` |  | **Opened By** — Who created the case. Could be agent or customer. FK → sys_user. |
| `resolved_by` | FK_REF | 100% | `sys_user` | `Denis Kerrutt` | `Denis Kerrutt` | **Resolved By** — Agent who closed/resolved the case. FK → sys_user. |
| `u_owned_by` | FK_REF | 100% | `sys_user` | `Denis Kerrutt` | `Denis Kerrutt` | **Owned By** — Case owner — may differ from assigned agent. FK → sys_user. |
| `u_last_assignee` | FK_REF | 100% | `sys_user` | `Denis Kerrutt` | `Denis Kerrutt` | **Last Assignee** — Previous agent before last reassignment. Useful for reassignment analysis. FK → sys_user. |
| `contact` | FK_REF | 80% | `customer_contact` | `03d0b4203b00ae9091e0703a85e45a45` |  | **Customer Contact** — Individual person at the customer who raised the case. FK → customer_contact. |
| `sys_created_by` | TEXT | 100% | — | `Christine.Balde` | cardinality: 5 | **Created By (username)** — Username of whoever created the record. Not a FK — plain string. |
| `sys_updated_by` | TEXT | 100% | — | `system` | cardinality: 1 | **Updated By (username)** — Username of last person to update. Usually 'system' for auto-updates. |

## Teams

| Field | Type | Fill | FK Table | Sample Value | All Values / Notes | Business Meaning |
|---|---|---|---|---|---|---|
| `assignment_group` | FK_REF | 100% | `sys_user_group` | `CA-Helpdesk` | `CA-Helpdesk` | **Team / Queue** — Team the case is assigned to. e.g. CA-Helpdesk. FK → sys_user_group. |
| `u_last_assignment_group` | FK_REF | 100% | `sys_user_group` | `CA-Helpdesk` | `CA-Helpdesk` | **Last Team** — Previous team before last reassignment. FK → sys_user_group. |

## Account

| Field | Type | Fill | FK Table | Sample Value | All Values / Notes | Business Meaning |
|---|---|---|---|---|---|---|
| `account` | FK_REF | 100% | `customer_account` | `Toronto Parking Authority HO` | `Toronto Parking Authority HO` | **Account** — Customer company. FK → customer_account. Core filter for all TPA reports. |
| `company` | FK_REF | 100% | `core_company` | `Toronto Parking Authority HO` | `Toronto Parking Authority HO` | **Company** — Usually same as account. FK → core_company. May differ for multi-entity clients. |

## Timestamps

| Field | Type | Fill | FK Table | Sample Value | All Values / Notes | Business Meaning |
|---|---|---|---|---|---|---|
| `opened_at` | DATETIME | 100% | — | `2025-04-10 18:30:17` → `10/04/2025 20:30:17` | cardinality: 10 | **Opened At** — When the customer submitted the case. START of lifecycle. Base for all KPIs. |
| `first_response_time` | DATETIME | 100% | — | `2025-04-10 18:38:51` → `10/04/2025 20:38:51` | cardinality: 10 | **First Response At** — When agent first responded. first_response_time - opened_at = first response duration. |
| `assigned_on` | DATETIME | 100% | — | `2025-04-10 18:34:48` → `10/04/2025 20:34:48` | cardinality: 10 | **Assigned At** — When case was assigned to current agent. assigned_on - opened_at = time to assign. |
| `resolved_at` | DATETIME | 100% | — | `2025-04-10 18:38:51` → `10/04/2025 20:38:51` | cardinality: 10 | **Resolved At** — When case was marked resolved. KEY timestamp for resolution SLA. |
| `closed_at` | DATETIME | 100% | — | `2025-04-16 15:52:19` → `16/04/2025 17:52:19` | cardinality: 10 | **Closed At** — When the case was fully closed. |
| `sys_created_on` | DATETIME | 100% | — | `2025-04-10 18:30:18` → `10/04/2025 20:30:18` | cardinality: 10 | **Created At** — When record was created in ServiceNow. Usually same as opened_at. |
| `sys_updated_on` | DATETIME | 100% | — | `2025-04-16 15:52:19` → `16/04/2025 17:52:19` | cardinality: 10 | **Last Updated At** — Last time any field on this record was modified. |
| `u_date_of_occurrence` | DATE | 100% | — | `2025-04-10` → `10/04/2025` | cardinality: 9 | **Occurrence Date** — When the underlying problem/incident occurred. May predate case creation. |

## Effort & Workflow

| Field | Type | Fill | FK Table | Sample Value | All Values / Notes | Business Meaning |
|---|---|---|---|---|---|---|
| `time_worked` | DATETIME | 100% | — | `1970-01-01 00:15:00` → `15 Minutes` | cardinality: 2 | **Time Worked** — Agent effort logged on this case. e.g. 15 Minutes. Proxy for support cost. |
| `reassignment_count` | INTEGER | 100% | — | `0` | cardinality: 1 | **Reassignment Count** — How many times case moved between agents. High value = routing inefficiency. |
| `sys_mod_count` | INTEGER | 100% | — | `6` | cardinality: 7 | **Modification Count** — How many times this record was updated. Proxy for case complexity. |

## TPA Device/Location

| Field | Type | Fill | FK Table | Sample Value | All Values / Notes | Business Meaning |
|---|---|---|---|---|---|---|
| `u_tpl` | FK_REF | 100% | `customer_account` | `TPA -  CP125 - 343 Richmond` | `TPA -  CP125 - 343 Richmond`, `TPA - CP304 - 9 Wellesley West`, `TPA - LR - HO`, `Toronto Parking Authority` | **Parking Terminal** — TPA-specific. Physical parking terminal this case is about. FK → customer_account. KEY for geographic reporting. |
| `u_asset_device_type` | CHOICE | 100% | — | `1HW1CUP06` → `PTL` | `1HW1CUP03`→`Entry` / `1HW1CUP04`→`Exit` / `1HW1CUP06`→`No Device Type` / `1HW1CUP13`→`PKA` / `nodevicetype`→`PTL` | **Device Type** — TPA-specific. Type of parking hardware. e.g. PTL, reader. |
| `u_asset_device_number` | TEXT | 70% | — | `PK125` | cardinality: 6 | **Device Number** — TPA-specific. Specific device ID. e.g. PK125. |
| `u_fault_category` | CHOICE | 30% | — | `21` → `entervo.core` | `21`→`Entervo System Health Check` / `260`→`Hardware` / `666`→`entervo.core` | **Fault Category** — TPA-specific. Software module where fault occurred. e.g. entervo.core. |

## TPA Custom Fields

| Field | Type | Fill | FK Table | Sample Value | All Values / Notes | Business Meaning |
|---|---|---|---|---|---|---|
| `u_financial_impact` | CHOICE | 100% | — | `3` → `3 - Medium` | `3`→`3 - Medium` | **Financial Impact** — TPA-specific. Estimated financial impact level. e.g. 3 - Medium. |
| `u_operational_impact` | CHOICE | 100% | — | `3` → `3 - Medium` | `3`→`3 - Medium` | **Operational Impact** — TPA-specific. Operational disruption level. e.g. 3 - Medium. |
| `u_service_window` | FK_REF | 100% | `cmn_schedule` | `Mo-So 00:00-24:00` | `Mo-Fr 08:00-17:00`, `Mo-So 00:00-24:00` | **Service Window** — Business hours schedule applied to this case. FK → cmn_schedule. |
| `u_case_evaluation` | FK_REF | 100% | `u_case_evaluation` | `0 Seconds` | `0 Seconds`, `15 Minutes` | **Case Evaluation** — TPA-specific evaluation record linked to this case. FK → u_case_evaluation. |

## Flags

| Field | Type | Fill | FK Table | Sample Value | All Values / Notes | Business Meaning |
|---|---|---|---|---|---|---|
| `knowledge` | BOOLEAN | 100% | — | `false` | `false` | **Knowledge Article** — true = a KB article was linked to this case. |
| `proactive` | BOOLEAN | 100% | — | `false` | `false` | **Proactive Case** — true = case was opened proactively by support, not by customer request. |
| `needs_attention` | BOOLEAN | 100% | — | `false` | `false` | **Needs Attention** — Flag for manager review. Cases with issues or delays. |
| `u_has_incident` | BOOLEAN | 100% | — | `false` | `false` | **Has Incident** — true = a related incident record exists. |
| `u_quality_check` | BOOLEAN | 100% | — | `false` | `false` | **Quality Check Done** — true = case went through quality review process. |
| `u_best_practice_article` | BOOLEAN | 100% | — | `false` | `false` | **Best Practice** — true = a best practice article exists for this case type. |

## References

| Field | Type | Fill | FK Table | Sample Value | All Values / Notes | Business Meaning |
|---|---|---|---|---|---|---|
| `case_report` | FK_REF | 100% | `sn_customerservice_case_report` | `CSR0337596` | `CSR0337596`, `CSR0337598`, `CSR0357944`, `CSR0357952`, `CSR0359266` | **Case Report** — Linked case report record. FK → sn_customerservice_case_report. |
| `approval` | CHOICE | 100% | — | `not requested` → `Not Yet Requested` | `not requested`→`Not Yet Requested` | **Approval Status** — Whether case required approval. Usually 'Not Yet Requested'. |
| `notify` | CHOICE | 100% | — | `1` → `Do Not Notify` | `1`→`Do Not Notify` | **Notify Setting** — Notification preference. e.g. Do Not Notify. |

## System / Metadata

| Field | Type | Fill | FK Table | Sample Value | All Values / Notes | Business Meaning |
|---|---|---|---|---|---|---|
| `sys_domain` | FK_REF | 100% | `sys_user_group` | `global` |  | **Domain** — Multi-tenancy domain. Always 'global' in single-tenant instances. FK → sys_user_group (unexpected). |
| `sys_domain_path` | TEXT | 100% | — | `/` | cardinality: 1 | **Domain Path** — Always '/'. Safe to ignore for reporting. |
| `notes_to_comments` | BOOLEAN | 100% | — | `false` | `false`, `true` | **Notes to Comments** — Internal workflow flag — whether work notes were converted to comments. |

## Other Populated Fields

| Field | Type | Fill | FK Table | Sample Value | All Values / Notes | Business Meaning |
|---|---|---|---|---|---|---|
| `u_action_required` | TEXT | 100% | — | `None` | cardinality: 1 | **u_action_required** — ⚠️ *fill in* |
| `u_twelve_weeks_case_closed` | BOOLEAN | 100% | — | `false` | `false` | **u_twelve_weeks_case_closed** — ⚠️ *fill in* |
| `u_patch_2025` | BOOLEAN | 100% | — | `false` | `false` | **u_patch_2025** — ⚠️ *fill in* |
| `u_customer_notify` | BOOLEAN | 100% | — | `false` | `false` | **u_customer_notify** — ⚠️ *fill in* |
| `u_steps_taken` | TEXT | 100% | — | `TEST` | cardinality: 10 | **u_steps_taken** — ⚠️ *fill in* |
| `u_is_it_ok_to_contact_you_on_your_phone` | BOOLEAN | 100% | — | `false` | `false` | **u_is_it_ok_to_contact_you_on_your_phone** — ⚠️ *fill in* |
| `u_total_working_time` | DATETIME | 100% | — | `1970-01-01 00:00:00` → `0 Seconds` | cardinality: 2 | **u_total_working_time** — ⚠️ *fill in* |
| `follow_the_sun` | BOOLEAN | 100% | — | `false` | `false` | **follow_the_sun** — ⚠️ *fill in* |
| `u_no_further_action_required` | BOOLEAN | 100% | — | `false` | `false` | **u_no_further_action_required** — ⚠️ *fill in* |
| `upon_reject` | CHOICE | 100% | — | `cancel` → `Cancel all future Tasks` | `cancel`→`Cancel all future Tasks` | **upon_reject** — ⚠️ *fill in* |
| `sync_driver` | BOOLEAN | 100% | — | `false` | `false` | **sync_driver** — ⚠️ *fill in* |
| `u_reproducible` | BOOLEAN | 100% | — | `false` | `false`, `true` | **u_reproducible** — ⚠️ *fill in* |
| `short_description` | TEXT | 100% | — | `TEST` | cardinality: 10 | **short_description** — ⚠️ *fill in* |
| `u_create_kb_acticle` | BOOLEAN | 100% | — | `false` | `false` | **u_create_kb_acticle** — ⚠️ *fill in* |
| `u_escalation_counter` | INTEGER | 100% | — | `0` | cardinality: 1 | **u_escalation_counter** — ⚠️ *fill in* |
| `upon_approval` | CHOICE | 100% | — | `proceed` → `Proceed to Next Task` | `proceed`→`Proceed to Next Task` | **upon_approval** — ⚠️ *fill in* |
| `u_case_from_wo` | BOOLEAN | 100% | — | `false` | `false` | **u_case_from_wo** — ⚠️ *fill in* |
| `u_is_signed_confirmed` | BOOLEAN | 100% | — | `false` | `false` | **u_is_signed_confirmed** — ⚠️ *fill in* |
| `u_info_product_management` | BOOLEAN | 100% | — | `false` | `false` | **u_info_product_management** — ⚠️ *fill in* |
| `u_fixed_rate_time_worked` | BOOLEAN | 100% | — | `false` | `false` | **u_fixed_rate_time_worked** — ⚠️ *fill in* |
| `u_four_weeks_case_closed` | BOOLEAN | 100% | — | `false` | `false` | **u_four_weeks_case_closed** — ⚠️ *fill in* |
| `u_description_error` | TEXT | 100% | — | `TEST` | cardinality: 10 | **u_description_error** — ⚠️ *fill in* |
