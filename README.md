# Supply Chain Risk Monitor
### A data analysis project by [Your Name]

---

## Client Brief

A major CPG company with ~$98M in annual supplier spend across six commodity categories needs to identify which suppliers pose the greatest operational risk heading into Q3. The VP of Operations has three questions:

1. **Which input categories are most price-volatile right now?**
2. **Where are we dangerously exposed to a single supplier?**
3. **Which suppliers should we prioritize for risk mitigation this quarter?**

This project ingests commodity price data, joins it against a supplier master, runs SQL-based risk analysis, and delivers a prioritized action list.

---

## The Answer (Executive Summary)

**Two suppliers require immediate attention:**

| Supplier | Issue | Annual Spend | Action |
|---|---|---|---|
| National Freight Solutions | Sole-source logistics, $18M spend | $18.0M | Qualify backup carrier within 60 days |
| Caribbean Sugar Partners | Sole-source, 60-day lead time, no buffer | $7.8M | Dual-source or increase safety stock |

**Crude oil** is the most volatile input (8.5% swing in 90 days), flowing through to diesel costs — which are fully concentrated in one logistics provider.

**Corn inputs** are the lowest risk category — three suppliers, no sole-source dependency.

---

## Project Structure

```
supply_chain/
├── 01_setup_db.py        # Build SQLite schema, seed supplier data
├── 02_generate_data.py   # Generate realistic commodity price time series
├── 03_analysis.py        # SQL risk queries (volatility, concentration, lead time)
├── 04_visualizations.py  # Plotly charts — 5 output files
├── supply_chain.db       # SQLite database (generated)
└── output/
    ├── 01_commodity_trends.html         # Price index over time
    ├── 02_supplier_risk_matrix.html     # Spend vs risk bubble chart
    ├── 03_concentration_risk.html       # Sole-source exposure by category
    ├── 04_price_volatility.html         # 90-day price swing by commodity
    └── 05_executive_summary_table.html  # Top 8 highest-risk suppliers
```

---

## Methodology

### Risk Score Components
Each supplier receives a **composite risk score (0–100)** built from three signals:

| Signal | Weight | Definition |
|---|---|---|
| Sole-source flag | 40% | Binary: only supplier for this input category |
| Lead time risk | 30% | Lead time vs category average, normalized |
| Spend weight | 30% | Annual spend as % of max supplier spend |

### SQL Queries
Four analytical queries drive the risk assessment:
- **`price_volatility_90d`** — % price swing per commodity over last 90 days
- **`sole_source_exposure`** — % of category spend with no backup supplier
- **`lead_time_risk`** — suppliers above their category average lead time
- **`top_risk_suppliers`** — composite score joining all signals

---

## How to Run

```bash
# Install dependencies
pip install pandas plotly requests

# Step 1: Build database and seed suppliers
python3 01_setup_db.py

# Step 2: Generate commodity price data
python3 02_generate_data.py

# Step 3: Run SQL analysis (prints results to console)
python3 03_analysis.py

# Step 4: Generate visualizations
python3 04_visualizations.py

# Open any chart in your browser
open output/02_supplier_risk_matrix.html
```

---

## Key Findings

### 1. Sole-Source Concentration
Five of six commodity categories have at least one sole-source supplier. The **diesel/logistics** category is the highest risk: $18M in annual spend with a single carrier and no backup qualified.

### 2. Price Volatility
Crude oil showed an **8.5% price swing** in the last 90 days — the highest of any input category. This flows directly into diesel costs and, by extension, into the sole-source logistics risk above. These two risks compound each other.

### 3. Lead Time Outliers
Caribbean Sugar Partners has a **60-day lead time** — 23 days above the category average — and is sole-source. Any disruption in their supply chain leaves zero buffer time.

### 4. Lower Risk Areas
Corn inputs are well-diversified (three suppliers, no sole-source dependency, stable recent pricing). This category can be deprioritized for Q3 risk mitigation effort.

---

## Recommended Actions

| Priority | Action | Supplier | Timeline |
|---|---|---|---|
| 🔴 High | Qualify backup logistics carrier | SUP_009 | 60 days |
| 🔴 High | Dual-source sugar supply or increase safety stock | SUP_015 | 90 days |
| 🟡 Medium | Renegotiate metals contract with price escalation cap | SUP_014 | Q3 |
| 🟡 Medium | Qualify second plastics supplier | SUP_001 | Q3 |
| 🟢 Low | Monitor crude oil — triggers diesel cost review if >10% swing | N/A | Ongoing |

---

## Tech Stack

- **Python** — pandas, plotly, numpy, sqlite3
- **SQL** — SQLite with window functions (LAG, PARTITION BY), CTEs
- **Data** — Synthetic time series calibrated to real commodity price behavior (GBM model with shock events and seasonality)

---

## Background

This project was inspired by real supply chain visibility gaps observed during an operations internship at a major CPG company. The analytical framework mirrors how platforms like Palantir Foundry approach supplier risk — connecting commodity market signals to internal supplier master data to surface actionable operational decisions.
