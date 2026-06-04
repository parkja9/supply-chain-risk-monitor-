"""
Supply Chain Risk Monitor
Step 4: Visualizations — framed as a client deliverable
Charts that answer a VP of Operations' actual questions
"""

import sqlite3
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

DB_PATH = "supply_chain.db"
OUT_DIR = "output"

import os
os.makedirs(OUT_DIR, exist_ok=True)

COLORS = {
    "High":   "#E24B4A",
    "Medium": "#EF9F27",
    "Low":    "#1D9E75",
    "line":   "#378ADD",
    "bg":     "#FFFFFF",
    "grid":   "#F1EFE8",
    "text":   "#2C2C2A",
    "muted":  "#888780",
}

def base_layout(title, subtitle=""):
    return dict(
        title=dict(
            text=f"<b>{title}</b><br><sup style='color:{COLORS['muted']}'>{subtitle}</sup>",
            font=dict(size=16, color=COLORS["text"]),
            x=0.02,
        ),
        paper_bgcolor=COLORS["bg"],
        plot_bgcolor=COLORS["bg"],
        font=dict(family="Arial", size=12, color=COLORS["text"]),
        margin=dict(l=60, r=40, t=80, b=60),
        xaxis=dict(gridcolor=COLORS["grid"], showgrid=True),
        yaxis=dict(gridcolor=COLORS["grid"], showgrid=True),
    )

def chart_1_commodity_trends(conn):
    df = pd.read_sql("""
        SELECT commodity, date, price
        FROM commodity_prices
        WHERE date >= '2022-01-01'
        ORDER BY commodity, date
    """, conn)
    df["date"] = pd.to_datetime(df["date"])
    commodity_labels = {
        "crude_oil":    "Crude Oil (USD/bbl)",
        "diesel":       "Diesel (USD/gal)",
        "corn_ppi":     "Corn PPI",
        "plastics_ppi": "Plastics PPI",
        "metals_ppi":   "Metals PPI",
        "sugar_ppi":    "Sugar PPI",
    }
    palette = ["#378ADD", "#E24B4A", "#1D9E75", "#EF9F27", "#534AB7", "#D85A30"]
    fig = go.Figure()
    for i, (comm, label) in enumerate(commodity_labels.items()):
        sub = df[df["commodity"] == comm].copy()
        if sub.empty:
            continue
        base = sub.sort_values("date").iloc[0]["price"]
        sub["indexed"] = sub["price"] / base * 100
        fig.add_trace(go.Scatter(
            x=sub["date"], y=sub["indexed"].round(1),
            name=label, mode="lines",
            line=dict(color=palette[i % len(palette)], width=2),
        ))
    fig.update_layout(**base_layout("Input Cost Index — All Commodities", "Indexed to Jan 2022 = 100  |  Source: FRED"))
    fig.update_yaxes(title="Index (Jan 2022 = 100)")
    fig.write_html(f"{OUT_DIR}/01_commodity_trends.html")
    print("Saved: 01_commodity_trends.html")

def chart_2_risk_matrix(conn):
    df = pd.read_sql("""
        SELECT s.supplier_name, s.commodity_category,
               s.annual_spend_usd / 1e6 AS spend_m,
               s.sole_source, s.lead_time_days,
               r.composite_risk_score, r.risk_tier
        FROM suppliers s
        JOIN risk_scores r USING (supplier_id)
        ORDER BY composite_risk_score DESC
    """, conn)
    fig = px.scatter(
        df, x="spend_m", y="composite_risk_score",
        size="lead_time_days", color="risk_tier",
        color_discrete_map={"High": COLORS["High"], "Medium": COLORS["Medium"], "Low": COLORS["Low"]},
        hover_name="supplier_name",
        hover_data={"commodity_category": True, "spend_m": ":.2f", "lead_time_days": True, "sole_source": True, "composite_risk_score": ":.1f", "risk_tier": False},
        labels={"spend_m": "Annual Spend ($M)", "composite_risk_score": "Composite Risk Score (0–100)", "lead_time_days": "Lead Time (days)"},
        size_max=40,
    )
    fig.add_hline(y=60, line_dash="dot", line_color=COLORS["High"], annotation_text="High risk threshold", annotation_position="right")
    fig.add_hline(y=35, line_dash="dot", line_color=COLORS["Medium"], annotation_text="Medium risk threshold", annotation_position="right")
    fig.update_layout(**base_layout("Supplier Risk Matrix", "Bubble size = lead time days  |  Hover for details"))
    fig.write_html(f"{OUT_DIR}/02_supplier_risk_matrix.html")
    print("Saved: 02_supplier_risk_matrix.html")

def chart_3_concentration_risk(conn):
    df = pd.read_sql("""
        SELECT
            commodity_category,
            ROUND(SUM(annual_spend_usd)/1e6, 2) AS total_spend_m,
            ROUND(
                CAST(SUM(CASE WHEN sole_source=1 THEN annual_spend_usd ELSE 0 END) AS FLOAT)
                / SUM(annual_spend_usd) * 100, 1
            ) AS pct_sole_source
        FROM suppliers
        GROUP BY commodity_category
        ORDER BY pct_sole_source DESC
    """, conn)
    colors = [
        COLORS["High"] if p >= 80
        else COLORS["Medium"] if p >= 40
        else COLORS["Low"]
        for p in df["pct_sole_source"]
    ]
    fig = go.Figure(go.Bar(
        x=df["commodity_category"],
        y=df["pct_sole_source"],
        marker_color=colors,
        text=df["pct_sole_source"].apply(lambda x: f"{x}%"),
        textposition="outside",
    ))
    fig.add_hline(y=50, line_dash="dot", line_color=COLORS["muted"], annotation_text="50% threshold", annotation_position="right")
    fig.update_layout(**base_layout("Sole-Source Concentration by Input Category", "% of category spend with no backup supplier  |  Red = High risk"))
    fig.update_yaxes(title="% of Spend on Sole-Source Supplier", range=[0, 115])
    fig.update_xaxes(title="Input Category")
    fig.write_html(f"{OUT_DIR}/03_concentration_risk.html")
    print("Saved: 03_concentration_risk.html")

def chart_4_price_volatility(conn):
    df = pd.read_sql("""
        WITH recent AS (
            SELECT commodity, price
            FROM commodity_prices
            WHERE date >= DATE('now', '-90 days')
        )
        SELECT commodity,
               ROUND((MAX(price) - MIN(price)) / AVG(price) * 100, 1) AS pct_swing
        FROM recent
        GROUP BY commodity
        ORDER BY pct_swing DESC
    """, conn)
    colors = [COLORS["High"] if p >= 15 else COLORS["Medium"] if p >= 7 else COLORS["Low"] for p in df["pct_swing"]]
    fig = go.Figure(go.Bar(
        x=df["commodity"], y=df["pct_swing"],
        marker_color=colors,
        text=df["pct_swing"].apply(lambda x: f"{x}%"),
        textposition="outside",
    ))
    fig.update_layout(**base_layout("90-Day Price Volatility by Commodity", "% swing from min to max over last 90 days  |  Red = High volatility"))
    fig.update_yaxes(title="Price Swing (%)", range=[0, df["pct_swing"].max() * 1.3])
    fig.update_xaxes(title="Commodity")
    fig.write_html(f"{OUT_DIR}/04_price_volatility.html")
    print("Saved: 04_price_volatility.html")

def chart_5_executive_summary(conn):
    df = pd.read_sql("""
        SELECT
            s.supplier_name AS "Supplier",
            s.commodity_category AS "Input",
            s.region AS "Region",
            '$' || ROUND(s.annual_spend_usd/1e6, 1) || 'M' AS "Annual Spend",
            s.lead_time_days || ' days' AS "Lead Time",
            CASE WHEN s.sole_source=1 THEN 'Yes' ELSE 'No' END AS "Sole Source",
            r.composite_risk_score AS "Risk Score",
            r.risk_tier AS "Tier"
        FROM suppliers s
        JOIN risk_scores r USING (supplier_id)
        ORDER BY r.composite_risk_score DESC
        LIMIT 8
    """, conn)
    fig = go.Figure(go.Table(
        header=dict(values=list(df.columns), fill_color=COLORS["text"], font=dict(color="white", size=12), align="left", height=36),
        cells=dict(
            values=[df[c] for c in df.columns],
            fill_color=[["#F1EFE8" if i % 2 else "white" for i in range(len(df))] for _ in range(len(df.columns)-1)] + [[COLORS["High"] if t == "High" else COLORS["Medium"] if t == "Medium" else COLORS["Low"] for t in df["Tier"]]],
            font=dict(size=12), align="left", height=32,
        )
    ))
    fig.update_layout(title=dict(text="<b>Top 8 Highest-Risk Suppliers — Recommended for Immediate Review</b>", font=dict(size=15, color=COLORS["text"]), x=0.01), paper_bgcolor=COLORS["bg"], margin=dict(l=20, r=20, t=60, b=20), height=400)
    fig.write_html(f"{OUT_DIR}/05_executive_summary_table.html")
    print("Saved: 05_executive_summary_table.html")

if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    print("Generating charts...\n")
    chart_1_commodity_trends(conn)
    chart_2_risk_matrix(conn)
    chart_3_concentration_risk(conn)
    chart_4_price_volatility(conn)
    chart_5_executive_summary(conn)
    conn.close()
    print(f"\nAll charts saved to ./{OUT_DIR}/")
