# gold.dim_date

Calendar dimension with one row per day from `2020-01-01` to `2030-12-31`.

## Fields
- `date_key`: Integer surrogate key in `YYYYMMDD` form.
- `full_date`: Actual calendar date.
- `year`, `month`, `day`: Date parts for slicing.
- `week`: ISO week number used for weekly reporting.
- `weekday`: Day of week as an integer.

## How to use it
- Join facts on `*_date_key` when you need date labels or time grouping.
- Use `full_date` for exact day filtering; use `year`, `month`, and `week` for rollups.
- This table is safe to treat as the canonical date lookup for the gold layer.
