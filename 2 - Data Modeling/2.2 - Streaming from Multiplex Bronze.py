# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC
# MAGIC <div  style="text-align: center; line-height: 0; padding-top: 9px;">
# MAGIC   <img src="https://raw.githubusercontent.com/derar-alhussein/Databricks-Certified-Data-Engineer-Professional/main/Includes/images/orders.png" width="60%">
# MAGIC </div>

# COMMAND ----------

# MAGIC %run ../Includes/Copy-Datasets

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT cast(key AS STRING), cast(value AS STRING)
# MAGIC FROM bronze
# MAGIC LIMIT 20

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Check the raw data where order is in JSON format
# MAGIC SELECT cast(value AS STRING) as order_in_json, *
# MAGIC   FROM bronze
# MAGIC   WHERE topic = "orders"

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Parse the Order in JSON using from_json() function passing the structure.
# MAGIC SELECT v.*
# MAGIC FROM (
# MAGIC   SELECT from_json(cast(value AS STRING), "order_id STRING, order_timestamp Timestamp, customer_id STRING, quantity BIGINT, total BIGINT, books ARRAY<STRUCT<book_id STRING, quantity BIGINT, subtotal BIGINT>>") v
# MAGIC   FROM bronze
# MAGIC   WHERE topic = "orders")

# COMMAND ----------

## Stream from Broze table into Temperory View
(spark.readStream
      .table("bronze")
      .createOrReplaceTempView("bronze_tmp"))

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT v.*
# MAGIC FROM (
# MAGIC   SELECT from_json(cast(value AS STRING), "order_id STRING, order_timestamp Timestamp, customer_id STRING, quantity BIGINT, total BIGINT, books ARRAY<STRUCT<book_id STRING, quantity BIGINT, subtotal BIGINT>>") v
# MAGIC   FROM bronze_tmp
# MAGIC   WHERE topic = "orders")

# COMMAND ----------

# MAGIC %sql
# MAGIC -- populate another temp view for silver with some clean up processing
# MAGIC CREATE OR REPLACE TEMPORARY VIEW orders_silver_tmp AS
# MAGIC   SELECT v.*
# MAGIC   FROM (
# MAGIC     SELECT from_json(cast(value AS STRING), "order_id STRING, order_timestamp Timestamp, customer_id STRING, quantity BIGINT, total BIGINT, books ARRAY<STRUCT<book_id STRING, quantity BIGINT, subtotal BIGINT>>") v
# MAGIC     FROM bronze_tmp
# MAGIC     WHERE topic = "orders")

# COMMAND ----------

## Write the streamed data into Silver table
query = (spark.table("orders_silver_tmp")
               .writeStream
               .option("checkpointLocation", f"{checkpoint_path}/orders_silver")
               .trigger(availableNow=True)
               .table("orders_silver"))

query.awaitTermination()

# COMMAND ----------

####  THIS IS THE FINAL STREAMING FROM BRONZE TO SILVER
from pyspark.sql import functions as F

json_schema = "order_id STRING, order_timestamp Timestamp, customer_id STRING, quantity BIGINT, total BIGINT, books ARRAY<STRUCT<book_id STRING, quantity BIGINT, subtotal BIGINT>>"

query = (spark.readStream.table("bronze")
        .filter("topic = 'orders'")
        .select(F.from_json(F.col("value").cast("string"), json_schema).alias("v"))
        .select("v.*")
     .writeStream
        .option("checkpointLocation", f"{checkpoint_path}/orders_silver")
        .trigger(availableNow=True)
        .table("orders_silver"))

query.awaitTermination()

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT *
# MAGIC FROM orders_silver
