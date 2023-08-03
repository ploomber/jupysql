
/* This SQL file was produced by JupySQL, do not edit directly.
Edit the notebook where this snippet was defined */
/* {"with_": ["rated_high"]} */

with rated_high as (
select * from languages where rating > 10.5
),
/* SNIPPET BEGINS */

select * from rated_high where change > 1
/* SNIPPET ENDS */
