# Using the data in Power BI

The repository does not ship a `.pbit` template yet. Instead, Power BI Desktop can
read the same dbt marts that the Streamlit dashboard uses. Everything is local; no
cloud account is required. **All data is synthetic.**

Build the data first:

```bash
make all          # venv + dependencies, synthetic data, dbt build
make export       # optional: write marts to data/exports/*.parquet
```

## Option A: Parquet files (simplest, no driver needed)

1. Run `make export`. It writes one Parquet file per mart to `data/exports/`
   (`fct_sales`, `dim_date`, `dim_store`, `dim_product`, `dim_customer`,
   `mart_daily_sales`, `mart_margin`, `mart_basket`, `mart_inventory`, `mart_cohorts`).
2. In Power BI Desktop: **Get data > Parquet**, and paste the full file path
   (for example `C:\repos\retail-analytics-dashboard\data\exports\fct_sales.parquet`).
   Repeat for each table, or use **Get data > Folder** on `data/exports` and
   combine/filter by file name.
3. Re-run `make build export` and click **Refresh** in Power BI to pick up new data.

If you generate the data on a different machine (for example WSL or a dev
container), copy `data/exports/` to a path Windows can reach.

## Option B: DuckDB file via ODBC (live queries against `data/retail.duckdb`)

1. Install the DuckDB ODBC driver for Windows from the official DuckDB
   documentation (Client APIs > ODBC). Use a driver version compatible with the
   `duckdb` Python package listed in `requirements.txt`, because the database file
   format must match.
2. Create a DSN in **ODBC Data Sources (64-bit)** using the DuckDB driver and set
   `Database` to the full path of `data/retail.duckdb`. Enable read-only access if the
   driver offers it (`access_mode=READ_ONLY`).
3. In Power BI Desktop: **Get data > ODBC**, choose the DSN, and select the tables
   from the `main` schema. Ignore the `staging` schema: those are views over the raw
   files with paths relative to the repo root.
4. DuckDB allows only one writer. Close Power BI (or the ODBC connection) before
   running `make build` again, then refresh.

A community DuckDB connector for Power BI also exists; it works the same way but is
not maintained by this project.

## Suggested model

Create a star schema with single-direction relationships:

| From (many)                     | To (one)                   |
|---------------------------------|----------------------------|
| `fct_sales[order_date]`         | `dim_date[date_day]`       |
| `fct_sales[store_id]`           | `dim_store[store_id]`      |
| `fct_sales[product_id]`         | `dim_product[product_id]`  |
| `fct_sales[customer_id]`        | `dim_customer[customer_id]`|
| `mart_inventory[snapshot_date]` | `dim_date[date_day]`       |
| `mart_inventory[store_id]`      | `dim_store[store_id]`      |
| `mart_inventory[product_id]`    | `dim_product[product_id]`  |

Mark `dim_date` as the date table. `mart_cohorts` and `mart_basket` are
self-contained and do not need relationships.

Starter DAX measures:

```DAX
Net Revenue      = SUM ( fct_sales[net_revenue] )
Gross Margin     = SUM ( fct_sales[gross_margin] )
Gross Margin %   = DIVIDE ( [Gross Margin], [Net Revenue] )
Orders           = DISTINCTCOUNT ( fct_sales[order_id] )
Avg Order Value  = DIVIDE ( [Net Revenue], [Orders] )
Stockout Rate    = DIVIDE (
                       CALCULATE ( COUNTROWS ( mart_inventory ), mart_inventory[is_stockout] = TRUE () ),
                       COUNTROWS ( mart_inventory ) )
```

`customer_id` is blank for guest orders; filter it out for member-only visuals.
