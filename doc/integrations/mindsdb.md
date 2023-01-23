# Mindsdb integration
In this guide we'll show an integration with MindsDB.

We will use Jupysql to run queries on top of MindsDB.
Train the model on top of it via SQL.
Once the model is ready, we will use sklearn-evaluation to generate plots and evaluate our model.

MindsDB is a powerful machine learning platform that enables users to easily build and deploy predictive models. One of the key features of MindsDB is its integration with Jupysql, which allows users to connect to and query databases from Jupyter notebooks. In this article, we will take a deeper dive into the technical details of this integration, and provide examples of how it can be used in practice. We will explore a customer churn dataset and generate predictions if our customer will churn or not. Once we're done with that we will evaluate our model and see how easy it is through a single line of code.

The integration between Jupysql and MindsDB is made possible by the use of the sqlite3 library. This library allows for easy communication between the two systems, and enables users to connect to a wide variety of databases and warehouses, including Redshift, Snowflake, Big query, DuckDB, SQLite, MySQL, and PostgreSQL. Once connected, users can run SQL queries directly from the MindsDB environment, making it easy to extract data from databases and use it to train predictive models.

Let's look at an example of how this integration can be used. Suppose we have a database containing customer churn data, and we want to use this data to train a model that predicts if a customer will churn or not. First, we would need to connect to the database from our Jupyter notebook using the jupysql library. This can be done using the following code:



```python
# Install required packages
%pip install PyMySQL jupysql sklearn-evaluation --upgrade
```

    Note: you may need to restart the kernel to use updated packages.



```python
import pandas as pd
from sklearn_evaluation import plot

# Import jupysql Jupyter extension to create SQL cells
%load_ext sql
%config SqlMagic.autocommit=False
```

**You'd need to make sure your MindsDB is up and reachable for the next stages. You can use either the local or the cloud version.**

**Note:** you will need to adjust the connection string according to the instance you're trying to connect to (url, user, password).
In addition you'd need to load [the dataset file](https://github.com/mindsdb/mindsdb-examples/blob/master/classics/customer_churn/raw_data/WA_Fn-UseC_-Telco-Customer-Churn.csv) into the DB, follow this guide on [how to do it](https://docs.mindsdb.com/sql/create/file).


```python
%sql mysql+pymysql://YOUR_EMAIL:YOUR_PASSWORD@cloud.mindsdb.com:3306
```


```python
%sql SHOW TABLES FROM files;
```

    *  mysql+pymysql://ido%40ploomber.io:***@cloud.mindsdb.com:3306
    2 rows affected.





<table>
    <tr>
        <th>Tables_in_files</th>
    </tr>
    <tr>
        <td>churn</td>
    </tr>
    <tr>
        <td>home_rentals</td>
    </tr>
</table>




```sql
%%sql 
SELECT *
FROM files.churn
LIMIT 5;
```

    *  mysql+pymysql://ido%40ploomber.io:***@cloud.mindsdb.com:3306
    5 rows affected.





<table>
    <tr>
        <th>customerID</th>
        <th>gender</th>
        <th>SeniorCitizen</th>
        <th>Partner</th>
        <th>Dependents</th>
        <th>tenure</th>
        <th>PhoneService</th>
        <th>MultipleLines</th>
        <th>InternetService</th>
        <th>OnlineSecurity</th>
        <th>OnlineBackup</th>
        <th>DeviceProtection</th>
        <th>TechSupport</th>
        <th>StreamingTV</th>
        <th>StreamingMovies</th>
        <th>Contract</th>
        <th>PaperlessBilling</th>
        <th>PaymentMethod</th>
        <th>MonthlyCharges</th>
        <th>TotalCharges</th>
        <th>Churn</th>
    </tr>
    <tr>
        <td>7590-VHVEG</td>
        <td>Female</td>
        <td>0</td>
        <td>Yes</td>
        <td>No</td>
        <td>1</td>
        <td>No</td>
        <td>No phone service</td>
        <td>DSL</td>
        <td>No</td>
        <td>Yes</td>
        <td>No</td>
        <td>No</td>
        <td>No</td>
        <td>No</td>
        <td>Month-to-month</td>
        <td>Yes</td>
        <td>Electronic check</td>
        <td>29.85</td>
        <td>29.85</td>
        <td>No</td>
    </tr>
    <tr>
        <td>5575-GNVDE</td>
        <td>Male</td>
        <td>0</td>
        <td>No</td>
        <td>No</td>
        <td>34</td>
        <td>Yes</td>
        <td>No</td>
        <td>DSL</td>
        <td>Yes</td>
        <td>No</td>
        <td>Yes</td>
        <td>No</td>
        <td>No</td>
        <td>No</td>
        <td>One year</td>
        <td>No</td>
        <td>Mailed check</td>
        <td>56.95</td>
        <td>1889.5</td>
        <td>No</td>
    </tr>
    <tr>
        <td>3668-QPYBK</td>
        <td>Male</td>
        <td>0</td>
        <td>No</td>
        <td>No</td>
        <td>2</td>
        <td>Yes</td>
        <td>No</td>
        <td>DSL</td>
        <td>Yes</td>
        <td>Yes</td>
        <td>No</td>
        <td>No</td>
        <td>No</td>
        <td>No</td>
        <td>Month-to-month</td>
        <td>Yes</td>
        <td>Mailed check</td>
        <td>53.85</td>
        <td>108.15</td>
        <td>Yes</td>
    </tr>
    <tr>
        <td>7795-CFOCW</td>
        <td>Male</td>
        <td>0</td>
        <td>No</td>
        <td>No</td>
        <td>45</td>
        <td>No</td>
        <td>No phone service</td>
        <td>DSL</td>
        <td>Yes</td>
        <td>No</td>
        <td>Yes</td>
        <td>Yes</td>
        <td>No</td>
        <td>No</td>
        <td>One year</td>
        <td>No</td>
        <td>Bank transfer (automatic)</td>
        <td>42.3</td>
        <td>1840.75</td>
        <td>No</td>
    </tr>
    <tr>
        <td>9237-HQITU</td>
        <td>Female</td>
        <td>0</td>
        <td>No</td>
        <td>No</td>
        <td>2</td>
        <td>Yes</td>
        <td>No</td>
        <td>Fiber optic</td>
        <td>No</td>
        <td>No</td>
        <td>No</td>
        <td>No</td>
        <td>No</td>
        <td>No</td>
        <td>Month-to-month</td>
        <td>Yes</td>
        <td>Electronic check</td>
        <td>70.7</td>
        <td>151.65</td>
        <td>Yes</td>
    </tr>
</table>




```sql
%%sql
CREATE MODEL mindsdb.customer_churn_predictor
FROM files
  (SELECT * FROM churn)
PREDICT Churn;
```

    *  mysql+pymysql://ido%40ploomber.io:***@cloud.mindsdb.com:3306
    0 rows affected.
    []


## Training the model

Training the model have 3 different statuses: Generating, Training, Complete.
Since it's a pretty small dataset it'd take a few minutes to get to the complete status.

Once the status is "complete", move on to the next section.

**Waiting for the below cell to show complete**


```sql
%%sql
SELECT status
FROM mindsdb.models
WHERE name='customer_churn_predictor';
```

    *  mysql+pymysql://ido%40ploomber.io:***@cloud.mindsdb.com:3306
    1 rows affected.





<table>
    <tr>
        <th>status</th>
    </tr>
    <tr>
        <td>complete</td>
    </tr>
</table>



Now that our model is reeady to generate predictions, we can start using it.
In the cell below we'll start by getting a single prediction.

We are classifying if a user will churn, it's confidence and the explanation based on a few input parameters such as their internet service, if they have phone service, dependents and more.


```sql
%%sql
SELECT Churn, Churn_confidence, Churn_explain
FROM mindsdb.customer_churn_predictor
WHERE SeniorCitizen=0
AND Partner='Yes'
AND Dependents='No'
AND tenure=1
AND PhoneService='No'
AND MultipleLines='No phone service'
AND InternetService='DSL';
```

    *  mysql+pymysql://ido%40ploomber.io:***@cloud.mindsdb.com:3306
    1 rows affected.





<table>
    <tr>
        <th>Churn</th>
        <th>Churn_confidence</th>
        <th>Churn_explain</th>
    </tr>
    <tr>
        <td>Yes</td>
        <td>0.7752808988764045</td>
        <td>{&quot;predicted_value&quot;: &quot;Yes&quot;, &quot;confidence&quot;: 0.7752808988764045, &quot;anomaly&quot;: null, &quot;truth&quot;: null, &quot;probability_class_No&quot;: 0.4756, &quot;probability_class_Yes&quot;: 0.5244}</td>
    </tr>
</table>



We can get a batch of multiple entries.

In the cell bellow we're getting 5 rows (customers) with different parameters such as monthly charges and contract type.


```sql
%%sql
SELECT t.customerID, t.Contract, t.MonthlyCharges, m.Churn
FROM files.churn AS t
JOIN mindsdb.customer_churn_predictor AS m
LIMIT 5;
```

    *  mysql+pymysql://ido%40ploomber.io:***@cloud.mindsdb.com:3306
    5 rows affected.





<table>
    <tr>
        <th>customerID</th>
        <th>Contract</th>
        <th>MonthlyCharges</th>
        <th>Churn</th>
    </tr>
    <tr>
        <td>7590-VHVEG</td>
        <td>Month-to-month</td>
        <td>29.85</td>
        <td>Yes</td>
    </tr>
    <tr>
        <td>5575-GNVDE</td>
        <td>One year</td>
        <td>56.95</td>
        <td>No</td>
    </tr>
    <tr>
        <td>3668-QPYBK</td>
        <td>Month-to-month</td>
        <td>53.85</td>
        <td>Yes</td>
    </tr>
    <tr>
        <td>7795-CFOCW</td>
        <td>One year</td>
        <td>42.3</td>
        <td>No</td>
    </tr>
    <tr>
        <td>9237-HQITU</td>
        <td>Month-to-month</td>
        <td>70.7</td>
        <td>Yes</td>
    </tr>
</table>



## Classifier evaluation

Now that our model is ready, we want and should evaluate it.
We will query the actual and predicted values from MindsDB to evaluate our model.

Once we have the values we can plot them using sklearn-evaluation.
We will start first by getting all of our customers into a `pandas dataframe`.

**Note:** Take a close look on the query below, by saving it into a variable we can compose complex and longer queries.


```sql
%%sql result << SELECT t.customerID, t.Contract, t.MonthlyCharges, m.Churn, 
t.Churn as actual
FROM files.churn AS t
JOIN mindsdb.customer_churn_predictor AS m;
```

    *  mysql+pymysql://ido%40ploomber.io:***@cloud.mindsdb.com:3306
    7043 rows affected.


In the cell below, we're saving the query output into a dataframe.

We then, take the predicted churn values and the actual churn values into seperate variables.


```python
df = result.DataFrame()
y_pred = df.Churn
y_test = df.actual
```

## Plotting
Now that we have the values needed to evaluate our model, we can plot it into a confusion matrix:


```python
plot.ConfusionMatrix.from_raw_data(y_test, y_pred, normalize=False)
```


Additionally, we can generate a classification report for our model and compare it with other different models or previous iterations.


```python
target_names = ["No churn", "churn"]

report = plot.ClassificationReport.from_raw_data(
    y_test, y_pred, target_names=target_names
)
```
    


## Conclusion

In conclusion, the integration between Jupysql and MindsDB is a powerful tool for building and deploying predictive models. It allows easy data extraction and manipulation, and makes it simple to deploy models into production. This makes it a valuable tool for data scientists, machine learning engineers, and anyone looking to build predictive models. With this integration, the process of data extraction, cleaning, modeling, and deploying can all be done in one place: your Jupyter notebook. MindsDB on the other hand is making it a more efficient and streamlined process reducing the need for compute.
