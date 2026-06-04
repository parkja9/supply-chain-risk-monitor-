"""
Supply Chain Risk Monitor
Step 1: Build the SQLite database and seed supplier data
"""

import sqlite3
import pandas as pd
import random

random.seed(42)

DB_PATH = "supply_chain.db"

def create_schema(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS commodity_prices (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            commodity TEXT    NOT NULL,
            date      DATE    NOT NULL,
            price     REAL    NOT NULL,
            unit      TEXT,
            source    TEXT,
            UNIQUE(commodity, date)
        );

        CREATE TABLE IF NOT EXISTS suppliers (
            supplier_id        TEXT PRIMARY KEY,
            supplier_name      TEXT NOT NULL,
            region             TEXT,
            commodity_category TEXT,
            lead_time_days     INTEGER,
            annual_spend_usd   REAL,
            sole_source        INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS risk_scores (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_id         TEXT REFERENCES suppliers(supplier_id),
            score_date          DATE,
            price_volatility    REAL,
            concentration_risk  REAL,
            lead_time_risk      REAL,
            composite_risk_score REAL,
            risk_tier           TEXT
        );
    """)
    conn.commit()
    print("Schema created.")

def seed_suppliers(conn):
    """
    Simulates a CPG company's supplier master data.
    In a real Palantir engagement this would come from the client's ERP.
    """
    suppliers = [
        # Packaging suppliers
        ("SUP_001", "MidWest Plastics Co",       "Midwest",   "plastics_ppi",   14,  4_200_000, 1),
        ("SUP_002", "Great Lakes Packaging",      "Midwest",   "plastics_ppi",   18,  2_800_000, 0),
        ("SUP_003", "SouthPak Industries",        "Southeast", "plastics_ppi",   21,  1_500_000, 0),
        # Agricultural inputs
        ("SUP_004", "Iowa Grain Cooperative",     "Midwest",   "corn_ppi",        7,  8_900_000, 0),
        ("SUP_005", "Prairie Fields LLC",         "Midwest",   "corn_ppi",        9,  6_200_000, 0),
        ("SUP_006", "Delta Ag Supply",            "Southeast", "corn_ppi",       12,  1_100_000, 0),
        # Oils and fats
        ("SUP_007", "Gulf Coast Oils",            "South",     "crude_oil",      30, 12_500_000, 1),
        ("SUP_008", "Coastal Energy Partners",    "South",     "crude_oil",      45,  3_300_000, 0),
        # Transport / fuel-exposed
        ("SUP_009", "National Freight Solutions", "National",  "diesel",          3, 18_000_000, 1),
        ("SUP_010", "Regional Carriers Inc",      "Midwest",   "diesel",          5,  6_700_000, 0),
        ("SUP_011", "FastLane Logistics",         "West",      "diesel",          4,  2_200_000, 0),
        # Aluminum / metals (can manufacturing)
        ("SUP_012", "Allegiant Metals",           "Northeast", "metals_ppi",     25,  9_400_000, 0),
        ("SUP_013", "Apex Aluminum Group",        "West",      "metals_ppi",     30,  5_600_000, 0),
        ("SUP_014", "Eastern Steel & Alloys",     "Northeast", "metals_ppi",     28,  3_100_000, 1),
        # Sugar
        ("SUP_015", "Caribbean Sugar Partners",   "Southeast", "sugar_ppi",      60,  7_800_000, 1),
        ("SUP_016", "Domestic Sweeteners Co",     "Midwest",   "sugar_ppi",      14,  4_400_000, 0),
    ]

    df = pd.DataFrame(suppliers, columns=[
        "supplier_id", "supplier_name", "region",
        "commodity_category", "lead_time_days",
        "annual_spend_usd", "sole_source"
    ])

    df.to_sql("suppliers", conn, if_exists="replace", index=False)
    print(f"Seeded {len(df)} suppliers.")
    return df

if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    create_schema(conn)
    df = seed_suppliers(conn)
    conn.close()

    print("\nSupplier summary:")
    print(df.groupby("commodity_category").agg(
        suppliers=("supplier_id", "count"),
        total_spend=("annual_spend_usd", "sum"),
        sole_source_count=("sole_source", "sum")
    ).to_string())
    print(f"\nTotal annual spend: ${df['annual_spend_usd'].sum():,.0f}")
    print(f"Sole-source suppliers: {df['sole_source'].sum()} of {len(df)}")
