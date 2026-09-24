# Pilot usage queries

Read-only Snowflake-style reference SQL against adapter-provided logical views. These are schema templates, not claims that a deployment already has these tables. Map or implement the views before executing; use bound values or the provider's safe parameter mechanism. Substitute `<org_uuid>` from CRM, `<window_days>` and `<use_case_sample>` from `policy.pilot_usage`, `<pilot_start>` from the report window. Return dates as ISO date text; the adapter must normalize any native date encoding.

Keep the first-line marker comment on queries 1, 4, and 5 unchanged. `assemble_pilot_usage_input.py` finds each saved result by that marker.

Check warehouse costs and timeouts with the configured adapter, especially for queries 2, 3, and 5 against `usage_queries`. When asynchronous execution is supported, submit all statements before polling their handles; otherwise use the adapter's synchronous operation.

Report mode runs 1, 1b, 2, 3. PDF mode runs 1, 4, 5 and, when the two page narratives need a query sample, 3.

## 1. Roster and activity

```sql
-- pilot_usage q1_roster
WITH roster AS (
  SELECT DISTINCT user_id, user_email
  FROM usage_roster_daily
  WHERE organization_uuid = '<org_uuid>' AND date_pt = CURRENT_DATE - 1 AND is_organization_user
),
a AS (
  SELECT user_id, date_pt, daily_query_count, daily_computer_query_count, l7_query_count
  FROM usage_activity_daily
  WHERE organization_uuid = '<org_uuid>' AND date_pt BETWEEN CURRENT_DATE - <window_days> AND CURRENT_DATE - 1
    AND user_id IN (SELECT user_id FROM roster)
)
SELECT r.user_email,
       TO_VARCHAR(MIN(CASE WHEN a.daily_query_count > 0 THEN a.date_pt END)) AS first_query,
       TO_VARCHAR(MAX(CASE WHEN a.daily_query_count > 0 THEN a.date_pt END)) AS last_query,
       MAX(CASE WHEN a.date_pt = CURRENT_DATE - 1 THEN a.l7_query_count END) AS l7_queries,
       SUM(a.daily_query_count) AS window_queries,
       SUM(a.daily_computer_query_count) AS window_computer_queries
FROM roster r
LEFT JOIN a ON a.user_id = r.user_id
GROUP BY 1
ORDER BY window_queries DESC NULLS LAST, r.user_email
```

Seats provisioned = row count. Active = `window_queries > 0`. Idle = null or 0. Task-product share = sum of `window_computer_queries` over sum of `window_queries`.

## 1b. Weekly trend

```sql
WITH roster AS (
  SELECT DISTINCT user_id
  FROM usage_roster_daily
  WHERE organization_uuid = '<org_uuid>' AND date_pt = CURRENT_DATE - 1 AND is_organization_user
)
SELECT TO_VARCHAR(DATE_TRUNC('week', date_pt)) AS week_start,
       COUNT(DISTINCT CASE WHEN daily_query_count > 0 THEN user_id END) AS active_users,
       SUM(daily_query_count) AS queries
FROM usage_activity_daily
WHERE organization_uuid = '<org_uuid>' AND date_pt BETWEEN CURRENT_DATE - <window_days> AND CURRENT_DATE - 1
  AND user_id IN (SELECT user_id FROM roster)
GROUP BY 1 ORDER BY 1
```

## 2. Feature mix and models

```sql
WITH roster AS (
  SELECT DISTINCT user_id
  FROM usage_roster_daily
  WHERE organization_uuid = '<org_uuid>' AND date_pt = CURRENT_DATE - 1 AND is_organization_user
)
SELECT CASE WHEN GROUPING(product_mode) = 0 THEN 'mode' ELSE 'model' END AS kind,
       COALESCE(product_mode, display_model) AS value,
       COUNT(*) AS queries, COUNT(DISTINCT user_id) AS users
FROM usage_queries
WHERE organization_uuid = '<org_uuid>' AND date_pt BETWEEN CURRENT_DATE - <window_days> AND CURRENT_DATE - 1
  AND user_id IN (SELECT user_id FROM roster)
GROUP BY GROUPING SETS ((product_mode), (display_model))
QUALIFY kind = 'mode' OR ROW_NUMBER() OVER (PARTITION BY kind ORDER BY queries DESC) <= 5
ORDER BY kind DESC, queries DESC
```

`mode` rows are complete, so the mix sums to 100 percent. `model` rows are the top five. `product_mode` legend: asi = the configured task product; search_mode = Search; chat_mode = Chat; study_mode, research_mode, scheduled_tasks, pro, and NULL roll into Other; display_model is the model. If this query is not available, report task-product share from query 1 and omit models.

## 3. Use-case sample

```sql
WITH roster AS (
  SELECT DISTINCT user_id, user_email
  FROM usage_roster_daily
  WHERE organization_uuid = '<org_uuid>' AND date_pt = CURRENT_DATE - 1 AND is_organization_user
),
recent AS (
  SELECT q.date_pt, q.query_submitted_at_utc, r.user_id, r.user_email, q.product_mode, q.query_string
  FROM usage_queries q
  JOIN roster r ON r.user_id = q.user_id
  WHERE q.organization_uuid = '<org_uuid>' AND q.date_pt BETWEEN CURRENT_DATE - <window_days> AND CURRENT_DATE - 1
    AND q.query_string IS NOT NULL
    AND LENGTH(q.query_string) BETWEEN 15 AND 2000
    AND q.query_string NOT LIKE '{%'
  ORDER BY q.date_pt DESC, q.query_submitted_at_utc DESC
  LIMIT 2000
)
SELECT TO_VARCHAR(date_pt) AS day, user_email, product_mode, LEFT(query_string, 120) AS query_text
FROM recent
QUALIFY ROW_NUMBER() OVER (PARTITION BY LEFT(query_string, 60) ORDER BY date_pt DESC) = 1
   AND ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY date_pt DESC, query_submitted_at_utc DESC) <= 8
ORDER BY date_pt DESC
LIMIT <use_case_sample>
```

The `recent` CTE caps the scan at the newest 2000 rows before the window functions run; this bounds the sampling window before the per-user and duplicate limits. At most 8 rows per user, so one heavy session cannot fill the sample. Cluster into at most five themes. Quote one example per theme, verbatim, at most 120 characters. Skip file names, JSON, and single words.

## 4. Credit grants (pdf mode)

```sql
-- pilot_usage q4_grants
SELECT user_email, billing_credit_name, billing_credit_category_enriched,
       TO_VARCHAR(effective_at_pt) AS effective_at, TO_VARCHAR(expires_at_pt) AS expires_at,
       TO_VARCHAR(voided_at_pt) AS voided_at, billing_credit_amount_dollars AS amount_dollars
FROM usage_credit_grants
WHERE organization_uuid = '<org_uuid>' AND credit_product_type = 'asi'
ORDER BY effective_at_pt
```

One row per grant, seat and pool, including voided and future-dated rows. The assemble script keeps rows with `voided_at` null and `effective_at` on or before data-through, sums `amount_dollars`, and multiplies by 100 for credits. Pilot start defaults to the earliest kept `effective_at`.

## 5. Tasks with credits (pdf mode)

```sql
-- pilot_usage q5_tasks
WITH roster AS (
  SELECT DISTINCT user_id, user_email
  FROM usage_roster_daily
  WHERE organization_uuid = '<org_uuid>' AND date_pt = CURRENT_DATE - 1 AND is_organization_user
),
tasks AS (
  SELECT b.context_uuid, b.user_id, MIN(b.date_pt) AS first_date, SUM(b.amount_cents) AS amount_cents
  FROM usage_task_billing b
  WHERE b.organization_uuid = '<org_uuid>' AND b.date_pt BETWEEN '<pilot_start>' AND CURRENT_DATE - 1
    AND b.user_id IN (SELECT TO_VARCHAR(user_id) FROM roster)
  GROUP BY 1, 2
),
first_q AS (
  SELECT q.context_uuid, q.query_string
  FROM usage_queries q
  WHERE q.organization_uuid = '<org_uuid>' AND q.date_pt BETWEEN '<pilot_start>' AND CURRENT_DATE - 1
    AND q.user_id IN (SELECT user_id FROM roster)
    AND q.context_uuid IN (SELECT context_uuid FROM tasks)
  QUALIFY ROW_NUMBER() OVER (PARTITION BY q.context_uuid ORDER BY q.query_submitted_at_utc) = 1
)
SELECT t.context_uuid, r.user_email, TO_VARCHAR(t.first_date) AS first_date,
       TO_VARCHAR(t.amount_cents) AS amount_cents, LEFT(f.query_string, 120) AS task_title
FROM tasks t
JOIN roster r ON TO_VARCHAR(r.user_id) = t.user_id
LEFT JOIN first_q f ON f.context_uuid = t.context_uuid
ORDER BY t.first_date, t.amount_cents DESC
```

One row per task (`context_uuid`). `amount_cents` is the raw billed sum; the assemble script rounds half up per task, then sums. `task_title` is the first prompt, 120 characters, for the category review only; it never prints in the PDF. `usage_task_billing` must expose only the configured task-product meter rows, scoped to the organization. The adapter must filter any mixed-product source before providing this view.

## View and date contract

The five logical views expose exactly the columns selected above, including organization_uuid on activity, query and billing views. Preserve source timezone semantics for date_pt and *_pt dates; convert timestamps before deriving a date. `asi` is a normalized task-product enum, not an assumed native value. A query adapter maps native product modes and excludes internal domains consistently. `CURRENT_DATE - 1` means yesterday in the deployment reporting timezone; replace it with the explicit reviewed data-through date for a historical report. Never interpolate an untrusted org ID or date directly into SQL.

Roster activity is a trailing-window report. PDF task credits are the reviewed pilot-start through data-through window. These scopes differ intentionally and must be labeled. A zero result requires a successful complete query. A failed or missing result is unavailable.
