---
jupytext:
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.14.5
kernelspec:
  display_name: Python 3 (ipykernel)
  language: python
  name: python3
myst:
  html_meta:
    description lang=en: Schedule ETL with JupySQL and GitHub actions
    keywords: jupyter, jupyterlab, sql, jupysql, github, ETL, Data engineering
    property=og:locale: en_US
---

# Schedule ETLs with Jupysql and GitHub actions

+++

![syntax](../static/syntax-highlighting-working.png)

## Introduction
In this short guide we will cover the basics of ETLs and Jupysql and how to perform 
ETLs through JupySQL and  scheduling a full ETL notebook via GitHub actions.

#### But first, what is an ETL?

`ETL` (Extract, Transform, Load) is a crucial process for data analytics and business intelligence. 
It involves extracting data from various sources, transforming it into a structured format, 
and loading it into a database or data warehouse. 
ETLs are an essential part of any data integration process, and they help businesses 
to make informed decisions based on their data.

#### Why JupySQL?
JupySQL is a powerful tool that allows you to interact with databases using 
SQL queries directly in Jupyter notebooks. We will start by discussing the importance 
of ETLs, followed by a brief introduction to JupySQL. 
Finally, we will dive into how to perform ETLs using JupySQL.

## Why ETLs are important?

ETLs play a significant role in data analytics and business intelligence. 
They help businesses to collect data from various sources, including social media, 
web pages, sensors, and other internal and external systems. By doing this, 
businesses can obtain a holistic view of their operations, customers, and market trends.

After extracting data, ETLs transform it into a structured format, such as a relational 
database, which allows businesses to analyze and manipulate data easily. 
By transforming data, ETLs can clean, validate, and standardize it, making it easier 
to understand and analyze.

Finally, ETLs load the data into a database or data warehouse, 
where businesses can access it easily. By doing this, 
ETLs enable businesses to access accurate and up-to-date information, 
allowing them to make informed decisions.

## What is JupySQL?

JupySQL (based on ipython-sql) is an extension for Jupyter notebooks that allows you 
to interact with databases using SQL queries. It provides a convenient way to access 
databases and data warehouses directly from Jupyter notebooks, allowing you to perform 
complex data manipulations and analyses.

JupySQL supports multiple database management systems, including SQLite, MySQL, 
PostgreSQL, DuckDB, Oracle, Snowflake and more (check out our integrations section 
on the left to learn more). You can connect to databases using standard connection 
strings or through the use of environment variables.

To use JupySQL, you need to install it using pip.
You can run the following command:

```python
pip install jupysql --quiet
```

Once installed, you can load the extension in Jupyter notebooks using the following command:

```python
%load_ext sql
```


After loading the extension, you can connect to a database using the following command:

```sh
#%sql dialect://username:password@host:port/database
```


For example, to connect to a SQLite database, you can use the following command:

```python
%sql sqlite:///mydatabase.db
```


## Performing ETLs using JupySQL

To perform ETLs using JupySQL, we will follow the standard ETL process, which involves 
the following steps:

1. Extract data
2. Transform data
3. Load data
4. Extract data

### Extract data
To extract data using JupySQL, we need to connect to the source database and execute 
a query to retrieve the data. For example, to extract data from a MySQL database, 
we can use the following command:

```python
%sql mysql://username:password@host:port/database
data = %sql SELECT * FROM mytable
```

This command connects to the MySQL database using the specified connection string 
and retrieves all the data from the "mytable" table. The data is stored in the 
"data" variable as a Pandas DataFrame.

**Note**: We can also use `%%sql df <<` to save the data into the `df` variable

### Transform data
After extracting data, it's often necessary to transform it into a format that's 
more suitable for analysis. This step may include cleaning data, filtering data, 
aggregating data, and combining data from multiple sources. Here are some common 
data transformation techniques:

* **Cleaning data**: Data cleaning involves removing or fixing errors, inconsistencies, 
   or missing values in the data. For example, you might remove rows with missing values, 
   replace missing values with the mean or median value, or fix typos or formatting errors.
* **Filtering data**: Data filtering involves selecting a subset of data that meets 
   specific criteria. For example, you might filter data to only include records 
   from a specific date range, or records that meet a certain threshold.
* **Aggregating data**: Data aggregation involves summarizing data by calculating 
   statistics such as the sum, mean, median, or count of a particular variable. 
   For example, you might aggregate sales data by month or by product category.
* **Combining data**: Data combination involves merging data from multiple sources 
   to create a single dataset. For example, you might combine data from different 
   tables in a relational database, or combine data from different files.

In JupySQL, you can use Pandas DataFrame methods to perform data transformations. 
For example, you can use the rename method to rename columns, the dropna method to 
remove missing values, and the astype method to convert data types.

Here's an example of how to use Pandas to transform data:
```python
# Rename columns
data = data.rename(columns={'old_column_name': 'new_column_name'})

# Remove missing values
data = data.dropna()

# Convert data types
data['date_column'] = data['date_column'].astype('datetime64[ns]')

# Filter data
filtered_data = data[data['sales'] > 1000]

# Aggregate data
monthly_sales = data.groupby(['year', 'month'])['sales'].sum()

# Combine data
merged_data = pd.merge(data1, data2, on='key_column')
```

**TODO**: In our example we'll use a simple transformation, cleaning NAs and renaming a column.

```python
# Rename columns
data = data.rename(columns={'old_column_name': 'new_column_name'})

# Remove missing values
data = data.dropna()
```

### Load data

After transforming the data, we need to load it into a destination database or 
data warehouse. We can use ipython-sql to connect to the destination database 
and execute SQL queries to load the data. For example, to load data into a PostgreSQL 
database, we can use the following command:

```python
%sql postgresql://username:password@host:port/database
%sql DROP TABLE IF EXISTS mytable;
%sql CREATE TABLE mytable (column1 datatype1, column2 datatype2, ...);
%sql COPY mytable FROM '/path/to/datafile.csv' DELIMITER ',' CSV HEADER;
```

This command connects to the PostgreSQL database using the specified connection 
string, drops the "mytable" table if it exists, creates a new table with the specified 
columns and data types, and loads the data from the CSV file.

## Scheduling on GitHub actions
The last step is executing our complete notebook via GitHub actions.
To do that we can use `ploomber-engine` which lets you schedule notebooks in a 
similar manner to papermill but in an external process.

We can use this sample ci.yml file and put it in our repository, the final file should
be located under `.github/workflows/ci.yml`:

```shell
# This is the ci.yml file
```


## Conclusion

ETLs are an essential process for data analytics and business intelligence. 
They help businesses to collect, transform, and load data from various sources, 
making it easier to analyze and make informed decisions. JupySQL is a powerful 
tool that allows you to interact with databases using SQL queries directly in Jupyter 
notebooks. Combined with Github actions we can create powerful workflows that
can be scheduled and help us get the data to its final stage.

By using JupySQL, you can perform ETLs easily and efficiently, 
allowing you to extract, transform, and load data in a structured format while 
Github actions allocate compute and set the environment.