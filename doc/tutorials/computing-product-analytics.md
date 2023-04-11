---
jupytext:
  notebook_metadata_filter: myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.14.5
kernelspec:
  display_name: Python 3 (ipykernel)
  language: python
  name: python3
---

# Conduct Product Analysis Using SQL

+++

Product analytics is a common analysis. This tutorial will provide a scenario for an e-commerce website and shows you how to conduct product analysis using SQL.

+++

## Growth and Retention

+++

Growth rate and user retention are some common metrics used in product analytics. Suppose that we have devleoped an app for Ploomber and want to see whether the app is popular. Here is some data we collected.

+++

### Dataset Description

For simplicity, we just use some small-scale randomly generated data. The dataset **user_activity** is consists of three columns: 
- User_id : the unique identifier of the user
- Month: the month where 
- Activity_count: the number of activity conduct by the user in that month. If the user never used this app before this month, this is considered as their sign-up month. 


| user_id | date       | activity_count |
|--------|------------|----------------|
| 1      | 2021-01-01 | 5              |
| 1      | 2021-02-01 | 3              |
| 1      | 2021-03-01 | 2              |
| 2      | 2021-01-01 | 10             |
| 3      | 2021-02-01 | 1              |
| 3      | 2021-03-01 | 0              |
| 4      | 2021-02-01 | 6              |
| 5      | 2021-01-01 | 4              |
| 5      | 2021-02-01 | 5              |
| 5      | 2021-03-01 | 6              |
| 6      | 2021-03-01 | 7              |
| 7      | 2021-03-01 | 10             |

```{code-cell} ipython3
:tags: [hide-output]

%pip install jupysql duckdb-engine --quiet
```

```{code-cell} ipython3
%load_ext sql
%sql duckdb://
```

Let's create the table by ourself first using SQL.

```{code-cell} ipython3
:tags: [hide-output]

%%sql
DROP TABLE IF EXISTS user_activity;
CREATE TABLE user_activity (
  user_id INT NOT NULL,
 date DATE NOT NULL,
  activity_count INT NOT NULL,
  PRIMARY KEY (user_id, date)
);
INSERT INTO user_activity (user_id, date, activity_count)
VALUES
  (1, '2021-01-01', 5),
  (1, '2021-02-01', 3),
  (1, '2021-03-01', 2),
  (2, '2021-01-01', 10),
  (3, '2021-02-01', 1),
  (3, '2021-03-01', 0),
  (4, '2021-02-01', 6),
  (5, '2021-01-01', 4),
  (5, '2021-02-01', 5),
  (5, '2021-03-01', 6),
  (6, '2021-03-01', 7),
  (7, '2021-03-01', 10);
```

Let's check our table using select.

```{code-cell} ipython3
:tags: [hide-output]

%%sql
SELECT * FROM user_activity
```

### Growth 

We defined growth rate to be the percentage increase of total number of users between each month. 

We first retrive the total number of users in each month

```{code-cell} ipython3
:tags: [hide-output]

%%sql
Select MONTH(date) as month, COUNT(DISTINCT user_id) AS total_users
FROM user_activity
GROUP BY MONTH(date)
```

Here, we group the dataset by the month of the date, then count the number of distinct users as our total number of users. This command will return the following output: 

| month | total_users       |
|--------|------------|
| 1      | 3|
| 2      | 4 |
| 3      | 5 |

+++

We save it using a temporary table called CTE. Then calculate using self join. 

```{tip}
'/' in sql between two integers conduct integer division only. For example, 10/3 would be 3 instead of 3.33333. As a result, we multiply the formula by 1.0 to convert it to float division. 
```

```{code-cell} ipython3
:tags: [hide-output]

%%sql
WITH CTE AS(
    Select MONTH(date) as month, COUNT(DISTINCT user_id) AS total_users
    FROM user_activity
    GROUP BY MONTH(date)
)
SELECT c1.month as PrevMonth, c2.month as CurrentMonth,ROUND((c2.total_users - c1.total_users)*1.0/c1.total_users*100, 2) AS Growth_Rate_in_Percentage
FROM CTE c1, CTE c2
WHERE c1.month = c2.month - 1
```

The growth January to February are 33.33% and 25%.

+++

The use of self join might be confusing. Here is a brief explanation of what self join is doing. After we run the command
`FROM CTE c1, CTE c2`
The table we get is a cartesian product of these three rows: 
| c1.month | c1.total_users| c2.month| c2.total_users|
|--------|------------|--------|------------|
| 1      | 3|1      | 3|
| 1      | 3|2      | 4 |
 1      | 3| 3| 5| 
| 2      | 4 |1|3|
| 2      | 4 |2|4|
| 2      | 4 |3|5|
| 3      | 5 |1|3|
| 3      | 5 |2|4|
| 3      | 5 |3|5|

+++

Then, with **WHERE c1.month = c2.month - 1**, we filter out the total number of users for subsequential months. The expected output is: 
| c1.month | c1.total_users| c2.month| c2.total_users|
|--------|------------|--------|------------|
| 1      | 3|2      | 4 |
| 2      | 4 |3|5|

As shown above, we calculate the final growth rate using c1.total_users and c2.total_users.

+++

### Retention

+++

Retention is a bit more complex. Every company might have a different definition of user retention. Here, we defiend retention as the percentage of users who still use the app one month after their first login.

+++

We first retrieve two tables. The first one is the number of first-login users in each month. We will create a temporary table called first_time_users to hold the results.

```{code-cell} ipython3
:tags: [hide-output]

%%sql
DROP TABLE IF EXISTS first_time_users;
CREATE TABLE first_time_users (
  month INT,
  first_time_users INT
);

INSERT INTO first_time_users (month, first_time_users)
SELECT MONTH(date) AS month, COUNT(DISTINCT u.user_id) AS first_time_users
FROM user_activity u
INNER JOIN (
  SELECT user_id, MIN(date) AS first_login
  FROM user_activity
  GROUP BY user_id
) t ON u.user_id = t.user_id AND u.date = t.first_login
GROUP BY MONTH(date);

SELECT * FROM first_time_users
```

This means that in January, 3 users start to use the app. Similarly, 2 start using in Febuary and 2 start using in March.

+++

Then we check the retention users (number of users who still use the app after one month of first-login) in each month.

```{code-cell} ipython3
:tags: [hide-output]

%%sql
DROP TABLE IF EXISTS retention_users;
CREATE TABLE retention_users (
  month INT,
  retention_users INT
);

INSERT INTO retention_users (month, retention_users)
SELECT MONTH(first_login) AS month, COUNT(DISTINCT u. user_id) AS retention_users
FROM user_activity u
INNER JOIN (
SELECT user_id, MIN(date) AS first_login
FROM user_activity
GROUP BY user_id) t 
ON u.user_id = t.user_id
WHERE MONTH(date) = MONTH(first_login) +1
GROUP BY MONTH(first_login);
SELECT * FROM retention_users
```

Here, the code that `WHERE MONTH(date) = MONTH(first_login) + 1` make sure that we only take users who still used the app at least one month behind into account. 
Only 2 users out of 3 continue to use the app after a month.

+++

Then, we combine these two table and make our calculation

We join the new_users and retention users based on the month we are looking at. Then, we make calculation for retention_rate.

```{code-cell} ipython3
:tags: [hide-output]

%%sql
SELECT f.month, first_time_users, IFNULL(retention_users, 0) AS retention_users, ROUND(retention_users * 1.0 / first_time_users, 4)*100 AS retention_rate
FROM first_time_users f 
FULL OUTER JOIN retention_users r
ON f.month = r.month
```