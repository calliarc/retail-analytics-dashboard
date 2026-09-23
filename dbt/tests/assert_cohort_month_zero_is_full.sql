-- Every cohort member is active in their acquisition month, by definition.
select *
from {{ ref('mart_cohorts') }}
where (months_since_first = 0 and active_customers <> cohort_size)
   or retention_rate not between 0 and 1
   or cumulative_repeat_rate not between 0 and 1
