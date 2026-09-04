{#
  History retention for silver.sys_user - the other half of CLAUDE.md finding
  #1 ("dims are not snapshotted"). Same idea as snapshots/sn_case_snapshot.sql:
  purely additive, reads silver.sys_user as-is, writes to a NEW table
  (snapshots.sys_user_snapshot). Nothing downstream reads it yet - this
  captures agent name/email/phone changes over time (e.g. an agent getting
  renamed, or their contact info updated), the same way the case snapshot
  captures state changes.

  Strategy: CHECK, not TIMESTAMP - deliberately different from
  sn_case_snapshot. silver.sys_user has no sys_updated_on column today (the
  ServiceNow field list for this table only just picked up sys_updated_on
  in this session's incremental-extraction work, and that hasn't been
  extracted/backfilled yet - see etl_core/api/config.py). A timestamp
  strategy needs a reliable "when did this last change" column to key off;
  without one, `check` is dbt's documented alternative: it compares the
  listed columns against the previous snapshot version and opens a new one
  only when one of them actually differs.

  check_cols deliberately excludes id/bronze_id/source_table/loaded_at/
  extraction_run_id - those are pipeline bookkeeping columns that change on
  every re-extraction regardless of whether the actual person's data
  changed. Including them would make this snapshot version on every run
  even when nothing real changed, defeating the point.

  Scope note - why this covers dim_agent but not dim_assignment_group or
  dim_terminal: dim_agent is enriched from a real, independently-extracted
  source table (silver.sys_user), so it has something meaningful to
  snapshot on its own. dim_assignment_group and dim_terminal have no such
  source - they're built entirely from denormalized columns living inside
  silver.sn_customerservice_case (assignment_group_sys_id/name,
  parking_terminal_sys_id/name - see models/gold/dim_assignment_group.sql
  and dim_terminal.sql). Whatever history exists for a group/terminal
  already rides along inside sn_case_snapshot's own versions (any case
  update that changes a case's group/terminal creates a new case snapshot
  version reflecting it) - there is no separate reference table for groups
  or terminals to snapshot independently, because this pipeline doesn't
  extract one from ServiceNow today. Snapshotting the same handful of
  distinct values pulled out of the case table a second time would not add
  any information sn_case_snapshot doesn't already have.
#}
{% snapshot sys_user_snapshot %}

{{
    config(
      target_schema='snapshots',
      unique_key='sys_id',
      strategy='check',
      check_cols=[
        'name', 'first_name', 'last_name', 'user_name',
        'email', 'mobile_phone', 'u_personal_id',
        'stockroom_sys_id', 'stockroom_name',
      ],
    )
}}

select *
from {{ source('silver', 'sys_user') }}

{% endsnapshot %}
