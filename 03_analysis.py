"""
Supply Chain Risk Monitor
Step 3: SQL-driven risk analysis — the core analytical layer
This is what a DS would build in Foundry. We're doing it in SQLite.
"""

import sqlite3
import pandas as pd

DB_PATH = "supply_chain.db"

QUERIES = {

    "price_volatility_90d": """
        -- 90-day price volatility per commodity
        -- High std dev = high input cost uncertainty
        WITH recent AS (
            SELECT
                commodity,
                price,
                date
            FROM commodity_prices
            WHERE date >= DATE('now', '-90 days')
        )
        SELECT
            commodity,
            COUNT(*)                          AS observations,
            ROUND(AVG(price), 2)              AS avg_price,
            ROUND(MAX(price) - MIN(price), 2) AS price_range,
            ROUND(
                (MAX(price) - MIN(price)) / AVG(price) * 100, 1
            )                                 AS pct_swing
        FROM recent
        GROUP BY commodity
        ORDER BY pct_swing DESC
    """,

    "sole_source_exposure": """
        -- How much spend is concentrated in sole-source suppliers?
        -- Sole source = no backup if they fail
        SELECT
            commodity_category,
            COUNT(*)                              AS total_suppliers,
            SUM(sole_source)                      AS sole_source_count,
            ROUND(SUM(annual_spend_usd) / 1e6, 2) AS total_spend_m,
            ROUND(
                SUM(CASE WHEN sole_source = 1
                    THEN annual_spend_usd ELSE 0 END)
                / SUM(annual_spend_usd) * 100, 1
            )                                     AS pct_spend_sole_source
        FROM suppliers
        GROUP BY commodity_category
        ORDER BY pct_spend_sole_source DESC
    """,

    "lead_time_risk": """
        -- Suppliers with lead times above their category average
        -- Long lead time = less buffer if something goes wrong
        WITH category_avg AS (
            SELECT
                commodity_category,
                AVG(lead_time_days) AS avg_lead_time
            FROM suppliers
            GROUP BY commodity_category
        )
        SELECT
            s.supplier_id,
            s.supplier_name,
            s.region,
            s.commodity_category,
            s.lead_time_days,
            ROUND(c.avg_lead_time, 1)              AS category_avg_days,
            ROUND(s.lead_time_days - c.avg_lead_time, 1) AS days_above_avg,
            ROUND(s.annual_spend_usd / 1e6, 2)    AS spend_m,
            s.sole_source
        FROM suppliers s
        JOIN category_avg c USING (commodity_category)
        WHERE s.lead_time_days > c.avg_lead_time
        ORDER BY days_above_avg DESC
    """,

    "recent_price_trend": """
        -- Month-over-month price change for most recent period
        -- Tells us which commodities are actively moving
        WITH monthly AS (
            SELECT
                commodity,
                STRFTIME('%Y-%m', date)  AS month,
                AVG(price)               AS avg_price
            FROM commodity_prices
            GROUP BY commodity, month
        ),
        with_lag AS (
            SELECT
                commodity,
                month,
                avg_price,
                LAG(avg_price) OVER (
                    PARTITION BY commodity ORDER BY month
                ) AS prev_month_price
            FROM monthly
        )
        SELECT
            commodity,
            month,
            ROUND(avg_price, 2)        AS avg_price,
            ROUND(prev_month_price, 2) AS prev_price,
            ROUND(
                (avg_price - prev_month_price)
                / prev_month_price * 100, 2
            )                          AS mom_pct_change
        FROM with_lag
        WHERE prev_month_price IS NOT NULL
        ORDER BY month DESC, ABS(mom_pct_change) DESC
        LIMIT 30
    """,

    "top_risk_suppliers": """
        -- Combine spend, sole-source, and lead time
        -- into a ranked supplier risk view
        WITH category_avg AS (
            SELECT commodity_category, AVG(lead_time_days) AS avg_lt
            FROM suppliers GROUP BY commodity_category
        ),
        scored AS (
            SELECT
                s.supplier_id,
                s.supplier_name,
                s.commodity_category,
                s.region,
                s.annual_spend_usd,
                s.sole_source,
                s.lead_time_days,
                c.avg_lt,
                -- risk signals (each 0-1)
                CASE WHEN s.sole_source = 1 THEN 1.0 ELSE 0.0 END
                    AS sole_src_flag,
                CASE
                    WHEN s.lead_time_days > c.avg_lt * 1.5 THEN 1.0
                    WHEN s.lead_time_days > c.avg_lt        THEN 0.5
                    ELSE 0.0
                END AS lead_risk,
                -- spend weighting: higher spend = higher impact if supplier fails
                s.annual_spend_usd / (
                    SELECT MAX(annual_spend_usd) FROM suppliers
                ) AS spend_weight
            FROM suppliers s
            JOIN category_avg c USING (commodity_category)
        )
        SELECT
            supplier_id,
            supplier_name,
            commodity_category,
            region,
            ROUND(annual_spend_usd / 1e6, 2) AS spend_m,
            sole_source,
            lead_time_days,
            ROUND(
                (sole_src_flag * 0.4 + lead_risk * 0.3 + spend_weight * 0.3) * 100
            , 1) AS composite_risk_score
        FROM scored
        ORDER BY composite_risk_score DESC
    """,
}

def run_analysis(conn):
    results = {}
    for name, sql in QUERIES.items():
        df = pd.read_sql(sql, conn)
        results[name] = df
        print(f"\n{'='*60}")
        print(f"  {name.replace('_', ' ').upper()}")
        print(f"{'='*60}")
        print(df.to_string(index=False))
    return results

def write_risk_scores(conn, results):
    """Write composite scores back to the risk_scores table."""
    df = results["top_risk_suppliers"].copy()
    df["score_date"] = pd.Timestamp.today().strftime("%Y-%m-%d")
    df["price_volatility"]   = None  # will add in step 4
    df["concentration_risk"] = None
    df["lead_time_risk"]     = None
    df["risk_tier"] = df["composite_risk_score"].apply(
        lambda x: "High" if x >= 60 else ("Medium" if x >= 35 else "Low")
    )
    out = df[[
        "supplier_id", "score_date",
        "price_volatility", "concentration_risk", "lead_time_risk",
        "composite_risk_score", "risk_tier"
    ]]
    out.to_sql("risk_scores", conn, if_exists="replace", index=False)
    print(f"\nWrote {len(out)} risk scores to DB.")

if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    results = run_analysis(conn)
    write_risk_scores(conn, results)
    conn.close()
