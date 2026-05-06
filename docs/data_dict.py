"""
04_data_dictionary.py
─────────────────────
Generates a markdown data dictionary from the saved JSON snapshot.

Output: data_dictionary.md — one row per non-empty field with:
  - True type (FK_REF, DATETIME, BOOLEAN, CHOICE, TEXT...)
  - Fill rate across all records
  - Sample raw value and display value
  - FK target table (if applicable)
  - All unique values for CHOICE and BOOLEAN fields
  - A business_meaning column you fill in manually

This document becomes your reference for the raw DDL and dbt models.
"""

import sys, os, json, glob
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from exploration.sn_helpers import profile_records

# ── Load ──────────────────────────────────────────────────────────────────────
project_root = os.path.dirname(os.path.dirname(__file__))
files = glob.glob(os.path.join(project_root, "data", "sn_data_*.json"))
if not files:
    raise FileNotFoundError("No data in ./data/sn_data_*.json")

latest = max(files, key=os.path.getmtime)
with open(latest, encoding="utf-8") as f:
    records = json.load(f)

# ── Profile ───────────────────────────────────────────────────────────────────

stats, N, ALL_FIELDS = profile_records(records)

# ── Business meaning hints — what we already know from exploration ─────────────
# Add your own notes here as you learn more about the data.
# Format: field_name → (short business name, meaning hint)

KNOWN = {
    # Identity
    "number":              ("Case Number",           "Human-readable case ID shown to customers. e.g. CS0395813"),
    "sys_id":              ("System ID",             "Internal 32-char UUID. Primary key for joins. Never shown in reports."),
    "task_effective_number":("Effective Number",     "Same as number in most cases. Used when case is linked to a parent task."),
    "case":                ("Case Title",            "Concatenation of prefix and number. UI display field."),
    "sys_class_name":      ("Record Type",           "Always 'sn_customerservice_case'. Confirms table type."),

    # Lifecycle
    "state":               ("Case State",            "Lifecycle stage. e.g. Open, In Progress, Closed, Resolved."),
    "active":              ("Is Active",             "true = case is open. false = closed or resolved."),
    "auto_close":          ("Auto Close Flag",       "true = case was closed automatically by the system, not by an agent."),
    "stage":               ("Stage",                 "More granular lifecycle stage within a state."),
    "escalation":          ("Escalation Level",      "Whether the case has been escalated. Normal = not escalated."),

    # Priority / Severity
    "priority":            ("Priority",              "Combined urgency + impact. 1=Critical, 2=High, 3=Medium, 4=Low."),
    "urgency":             ("Urgency",               "How quickly customer needs resolution. Input to priority calculation."),
    "impact":              ("Impact",                "Business impact of the issue. Input to priority calculation."),

    # Classification
    "category":            ("Category",              "Top-level case type. e.g. Corrective Maintenance."),
    "subcategory":         ("Subcategory",           "Second-level type under category."),
    "u_sub_category":      ("Custom Subcategory",    "TPA-specific. Remote = resolved without site visit. Onsite = field visit required."),
    "contact_type":        ("Channel",               "How the case was submitted. e.g. Portal, Email, Phone."),

    # Resolution
    "resolution_code":     ("Resolution Code",       "How the case was resolved. e.g. Non System Bug, Configuration Change."),
    "u_sub_code":          ("Resolution Sub-Code",   "TPA-specific drill-down on resolution. e.g. No Fault Found, Software Fix."),
    "cause":               ("Cause",                 "Root cause description entered by agent at close."),
    "close_notes":         ("Close Notes",           "Agent notes written at case closure."),

    # SLA
    "made_sla":            ("SLA Met",               "true = resolved within agreed SLA window. false = SLA breach."),
    "u_sla_breached":      ("SLA Breached (custom)", "TPA custom SLA breach flag. May track a different SLA definition than made_sla."),
    "sla_due":             ("SLA Deadline",          "Datetime by which case must be resolved per SLA contract."),

    # People
    "assigned_to":         ("Assigned Agent",        "Support agent currently responsible. FK → sys_user."),
    "opened_by":           ("Opened By",             "Who created the case. Could be agent or customer. FK → sys_user."),
    "resolved_by":         ("Resolved By",           "Agent who closed/resolved the case. FK → sys_user."),
    "u_owned_by":          ("Owned By",              "Case owner — may differ from assigned agent. FK → sys_user."),
    "u_last_assignee":     ("Last Assignee",         "Previous agent before last reassignment. Useful for reassignment analysis. FK → sys_user."),
    "contact":             ("Customer Contact",      "Individual person at the customer who raised the case. FK → customer_contact."),
    "sys_created_by":      ("Created By (username)", "Username of whoever created the record. Not a FK — plain string."),
    "sys_updated_by":      ("Updated By (username)", "Username of last person to update. Usually 'system' for auto-updates."),

    # Teams
    "assignment_group":    ("Team / Queue",          "Team the case is assigned to. e.g. CA-Helpdesk. FK → sys_user_group."),
    "u_last_assignment_group": ("Last Team",         "Previous team before last reassignment. FK → sys_user_group."),

    # Account
    "account":             ("Account",               "Customer company. FK → customer_account. Core filter for all TPA reports."),
    "company":             ("Company",               "Usually same as account. FK → core_company. May differ for multi-entity clients."),

    # Timestamps
    "opened_at":           ("Opened At",             "When the customer submitted the case. START of lifecycle. Base for all KPIs."),
    "closed_at":           ("Closed At",             "When the case was fully closed."),
    "resolved_at":         ("Resolved At",           "When case was marked resolved. KEY timestamp for resolution SLA."),
    "assigned_on":         ("Assigned At",           "When case was assigned to current agent. assigned_on - opened_at = time to assign."),
    "first_response_time": ("First Response At",     "When agent first responded. first_response_time - opened_at = first response duration."),
    "sys_created_on":      ("Created At",            "When record was created in ServiceNow. Usually same as opened_at."),
    "sys_updated_on":      ("Last Updated At",       "Last time any field on this record was modified."),
    "u_date_of_occurrence":("Occurrence Date",       "When the underlying problem/incident occurred. May predate case creation."),

    # Effort & Workflow
    "time_worked":         ("Time Worked",           "Agent effort logged on this case. e.g. 15 Minutes. Proxy for support cost."),
    "reassignment_count":  ("Reassignment Count",    "How many times case moved between agents. High value = routing inefficiency."),
    "sys_mod_count":       ("Modification Count",    "How many times this record was updated. Proxy for case complexity."),

    # Custom TPA Fields — Devices & Location
    "u_tpl":               ("Parking Terminal",      "TPA-specific. Physical parking terminal this case is about. FK → customer_account. KEY for geographic reporting."),
    "u_asset_device_type": ("Device Type",           "TPA-specific. Type of parking hardware. e.g. PTL, reader."),
    "u_asset_device_number":("Device Number",        "TPA-specific. Specific device ID. e.g. PK125."),
    "u_fault_category":    ("Fault Category",        "TPA-specific. Software module where fault occurred. e.g. entervo.core."),

    # Custom TPA Fields — Other
    "u_financial_impact":  ("Financial Impact",      "TPA-specific. Estimated financial impact level. e.g. 3 - Medium."),
    "u_operational_impact":("Operational Impact",    "TPA-specific. Operational disruption level. e.g. 3 - Medium."),
    "u_service_window":    ("Service Window",        "Business hours schedule applied to this case. FK → cmn_schedule."),
    "u_case_evaluation":   ("Case Evaluation",       "TPA-specific evaluation record linked to this case. FK → u_case_evaluation."),

    # Flags
    "knowledge":           ("Knowledge Article",     "true = a KB article was linked to this case."),
    "proactive":           ("Proactive Case",        "true = case was opened proactively by support, not by customer request."),
    "needs_attention":     ("Needs Attention",       "Flag for manager review. Cases with issues or delays."),
    "u_sla_breached":      ("SLA Breached",          "TPA custom SLA breach tracking flag."),
    "made_sla":            ("Made SLA",              "Standard SN SLA met flag."),
    "u_best_practice_article": ("Best Practice",     "true = a best practice article exists for this case type."),
    "u_has_incident":      ("Has Incident",          "true = a related incident record exists."),
    "u_quality_check":     ("Quality Check Done",    "true = case went through quality review process."),

    # References
    "case_report":         ("Case Report",           "Linked case report record. FK → sn_customerservice_case_report."),
    "approval":            ("Approval Status",       "Whether case required approval. Usually 'Not Yet Requested'."),
    "notify":              ("Notify Setting",        "Notification preference. e.g. Do Not Notify."),

    # Boilerplate (low value but keep)
    "sys_domain":          ("Domain",                "Multi-tenancy domain. Always 'global' in single-tenant instances. FK → sys_user_group (unexpected)."),
    "sys_domain_path":     ("Domain Path",           "Always '/'. Safe to ignore for reporting."),
    "notes_to_comments":   ("Notes to Comments",     "Internal workflow flag — whether work notes were converted to comments."),
}

# ── Section grouping order for the report ─────────────────────────────────────

SECTIONS = {
    "Identity":            ["number", "sys_id", "task_effective_number", "case", "sys_class_name"],
    "Lifecycle & Status":  ["state", "active", "auto_close", "stage", "escalation"],
    "Priority & Severity": ["priority", "urgency", "impact"],
    "Classification":      ["category", "subcategory", "u_sub_category", "contact_type"],
    "Resolution":          ["resolution_code", "u_sub_code", "cause", "close_notes"],
    "SLA":                 ["made_sla", "u_sla_breached", "sla_due"],
    "People":              ["assigned_to", "opened_by", "resolved_by", "u_owned_by",
                            "u_last_assignee", "contact", "sys_created_by", "sys_updated_by"],
    "Teams":               ["assignment_group", "u_last_assignment_group"],
    "Account":             ["account", "company"],
    "Timestamps":          ["opened_at", "first_response_time", "assigned_on",
                            "resolved_at", "closed_at", "sys_created_on",
                            "sys_updated_on", "u_date_of_occurrence"],
    "Effort & Workflow":   ["time_worked", "reassignment_count", "sys_mod_count"],
    "TPA Device/Location": ["u_tpl", "u_asset_device_type", "u_asset_device_number",
                            "u_fault_category"],
    "TPA Custom Fields":   ["u_financial_impact", "u_operational_impact",
                            "u_service_window", "u_case_evaluation"],
    "Flags":               ["knowledge", "proactive", "needs_attention",
                            "u_has_incident", "u_quality_check", "u_best_practice_article"],
    "References":          ["case_report", "approval", "notify"],
    "System / Metadata":   ["sys_domain", "sys_domain_path", "notes_to_comments"],
}

# Collect any populated field NOT already in a section
sectioned = {f for fields in SECTIONS.values() for f in fields}
# Fields that are completely empty across the snapshot (same rule as field_types.py)
empty_fields = {f for f, s in stats.items() if s["fill_pct"] == 0}

# Remaining are fields with some actual raw values (cardinality>0) excluding EMPTYs
remaining = [f for f, s in stats.items()
             if s["cardinality"] > 0 and f not in sectioned and f not in empty_fields]
if remaining:
    SECTIONS["Other Populated Fields"] = remaining


# ── Build markdown ─────────────────────────────────────────────────────────────

def md_escape(s):
    return str(s).replace("|", "\\|").replace("\n", " ").strip()


lines = []

lines.append("# Data Dictionary — sn_customerservice_case")
lines.append(f"\nGenerated from: `{os.path.basename(latest)}`  ")
lines.append(f"Records analyzed: **{N}**  ")
lines.append(f"Total fields: **{len(ALL_FIELDS)}** | Non-empty: **{sum(1 for s in stats.values() if s['fill_pct'] > 0)}** | Always empty: **{sum(1 for s in stats.values() if s['fill_pct'] == 0)}**\n")

lines.append(f"Excluded EMPTY fields: **{len(empty_fields)}** — these are always empty in the snapshot and omitted from sections.\n")

lines.append("## FK Tables Detected\n")
fk_tables = defaultdict(list)
for field, s in stats.items():
    if s.get("link_table"):
        fk_tables[s["link_table"]].append(field)
for tbl, fields in sorted(fk_tables.items()):
    lines.append(f"- **`{tbl}`** ← `{'`, `'.join(sorted(fields))}`")

lines.append("\n---\n")

for section_name, section_fields in SECTIONS.items():
    # Filter to only fields that exist and have real values (consistent with field_types.py: fill_pct > 0)
    active = [f for f in section_fields
              if f in stats and stats[f]["fill_pct"] > 0]
    if not active:
        continue

    lines.append(f"## {section_name}\n")
    lines.append("| Field | Type | Fill | FK Table | Sample Value | All Values / Notes | Business Meaning |")
    lines.append("|---|---|---|---|---|---|---|")

    for field in active:
        s       = stats[field]
        is_fk   = s["is_fk"]
        subtype = "FK_REF" if is_fk else (s["subtype"] or "TEXT")
        fill    = f"{s['fill_pct']}%"
        tbl     = f"`{s['link_table']}`" if s.get("link_table") else "—"

        # Sample value
        raw_s  = md_escape(s["sample_raw"]  or "")[:35]
        disp_s = md_escape(s["sample_disp"] or "")[:35]
        if is_fk:
            sample = f"`{disp_s}`" if disp_s else f"`{raw_s}`"
        elif disp_s and disp_s != raw_s:
            sample = f"`{raw_s}` → `{disp_s}`"
        else:
            sample = f"`{raw_s}`"

        # All values for CHOICE / BOOLEAN
        if subtype in ("CHOICE", "BOOLEAN") and s["cardinality"] <= 12:
            if subtype == "BOOLEAN":
                all_vals = ", ".join(f"`{v}`" for v in sorted(s["unique_raw"]))
            else:
                pairs    = list(zip(sorted(s["unique_raw"]), sorted(s["unique_disp"])))[:10]
                all_vals = " / ".join(f"`{r}`→`{d}`" for r, d in pairs)
        elif is_fk:
            disp_vals = sorted(s["unique_disp"])[:5]
            all_vals  = ", ".join(f"`{d}`" for d in disp_vals)
        else:
            all_vals = f"cardinality: {s['cardinality']}"

        # Business meaning
        known          = KNOWN.get(field, ("", ""))
        biz_name       = known[0] if known[0] else field
        biz_meaning    = md_escape(known[1]) if known[1] else "⚠️ *fill in*"

        lines.append(
            f"| `{field}` | {subtype} | {fill} | {tbl} | {sample} | {all_vals} | **{biz_name}** — {biz_meaning} |"
        )

    lines.append("")

# ── Write output ─────────────────────────────────────────────────────────────

out_dir  = os.path.join(project_root, "docs")
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "data_dictionary.md")

with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"  Data dictionary written to: {out_path}")
print(f"  {sum(1 for s in stats.values() if s['fill_pct'] > 0)} fields documented across {len(SECTIONS)} sections")
print(f"  Fields with ⚠️ fill in: {sum(1 for f in stats if stats[f]['fill_pct'] > 0 and f not in KNOWN)}")
