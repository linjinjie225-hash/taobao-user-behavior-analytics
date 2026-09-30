-- Core event counts
SELECT behavior, COUNT(*) AS events
FROM events
GROUP BY behavior
ORDER BY behavior;

-- Daily events and active users
SELECT event_date,
       COUNT(*) AS events,
       COUNT(DISTINCT user_id) AS active_users,
       SUM(CASE WHEN behavior = 'buy' THEN 1 ELSE 0 END) AS buy_events
FROM events
GROUP BY event_date
ORDER BY event_date;

-- Distinct-user behavior stages (not a session-sequential funnel)
WITH stages AS (
  SELECT user_id,
         MAX(CASE WHEN behavior = 'pv' THEN 1 ELSE 0 END) AS viewed,
         MAX(CASE WHEN behavior IN ('cart', 'fav') THEN 1 ELSE 0 END) AS engaged,
         MAX(CASE WHEN behavior = 'buy' THEN 1 ELSE 0 END) AS bought
  FROM events
  GROUP BY user_id
)
SELECT SUM(viewed) AS view_users,
       SUM(engaged) AS engaged_users,
       SUM(bought) AS buyer_users
FROM stages;

-- Multiple-purchase proxies
WITH buyer_activity AS (
  SELECT user_id,
         COUNT(*) AS buy_events,
         COUNT(DISTINCT event_date) AS purchase_days
  FROM events
  WHERE behavior = 'buy'
  GROUP BY user_id
)
SELECT COUNT(*) AS buyers,
       SUM(CASE WHEN buy_events >= 2 THEN 1 ELSE 0 END) AS repeat_event_buyers,
       SUM(CASE WHEN purchase_days >= 2 THEN 1 ELSE 0 END) AS repeat_day_buyers
FROM buyer_activity;

-- Category performance
SELECT category_id,
       SUM(CASE WHEN behavior = 'pv' THEN 1 ELSE 0 END) AS pv,
       SUM(CASE WHEN behavior = 'buy' THEN 1 ELSE 0 END) AS buy,
       1.0 * SUM(CASE WHEN behavior = 'buy' THEN 1 ELSE 0 END)
           / NULLIF(SUM(CASE WHEN behavior = 'pv' THEN 1 ELSE 0 END), 0) AS buy_to_pv_rate
FROM events
GROUP BY category_id
HAVING pv >= 100
ORDER BY buy DESC, pv DESC
LIMIT 20;

-- Category purchase-event ranking with a window function
WITH category_buy AS (
  SELECT category_id,
         SUM(CASE WHEN behavior = 'buy' THEN 1 ELSE 0 END) AS buy_events
  FROM events
  GROUP BY category_id
)
SELECT category_id,
       buy_events,
       DENSE_RANK() OVER (ORDER BY buy_events DESC) AS buy_rank
FROM category_buy
ORDER BY buy_rank, category_id
LIMIT 20;
