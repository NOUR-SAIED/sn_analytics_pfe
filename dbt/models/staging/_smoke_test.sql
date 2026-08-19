-- Smoke test only: proves the dbt compile -> run -> target-schema workflow
-- end to end (source() resolution, connection, materialization) before
-- anything real (the snapshot) depends on it. Safe to delete once that
-- confidence exists, or keep as a template for future staging models.
select *
from {{ source('silver', 'sn_customerservice_case') }}
limit 10
