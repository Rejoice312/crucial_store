import sqlite3
from pathlib import Path
from config import debug
import numpy as np
from datetime import datetime, timedelta

DB_PATH = Path(__file__).resolve().parent.parent / "crucial.db"
VALID_TRANSACTION_CATEGORIES = {
    'Sales',
    'Purchases',
    'Wages',
    'Loan Repayment',
    'Lending',
    'Other Expenses',
    'Capital',
    'Other Income',
    'Transportation',
    'Maintenance',
}
INFLOW_TRANSACTION_CATEGORIES = {'Sales', 'Loan Repayment', 'Other Income', 'Capital'}


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_transaction_flow_type(category: str) -> str:
    normalized_category = (category or '').strip()
    if normalized_category not in VALID_TRANSACTION_CATEGORIES:
        raise ValueError("invalid_category")
    return "Inflow" if normalized_category in INFLOW_TRANSACTION_CATEGORIES else "Outflow"


def create_tables() -> None:
    """Load schema from crucial.sql file"""
    schema_path = Path(__file__).resolve().parent.parent / "crucial.sql"
    with open(schema_path, 'r') as f:
        sql = f.read()
    conn = get_conn()
    with conn:
        conn.executescript(sql)


def _has_required_tables(conn: sqlite3.Connection) -> bool:
    existing = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('products', 'transactions')"
    ).fetchall()
    return len(existing) == 2


def init_db() -> None:
    """Initialize DB and rebuild the schema if the required tables are missing."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not DB_PATH.exists():
        create_tables()
        if debug:
            _seed_sample_data()
        return

    conn = get_conn()
    if not _has_required_tables(conn):
        with conn:
            conn.execute("DROP TABLE IF EXISTS transactions")
            conn.execute("DROP TABLE IF EXISTS products")
        create_tables()

    if debug:
        product_count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if product_count == 0:
            _seed_sample_data()


def _seed_sample_data() -> None:
    """Seed realistic sample data in the new transaction schema."""
    conn = get_conn()

    products = [
        ("T-Shirt", "Cotton T-Shirt", 120),
        ("Jeans", "Blue denim jeans", 85),
        ("Jacket", "Windbreaker jacket", 45),
        ("Sweater", "Wool sweater", 60),
        ("Shorts", "Summer shorts", 100),
    ]

    with conn:
        cur = conn.cursor()
        cur.executemany(
            "INSERT INTO products (name, description, stock_qty) VALUES (?, ?, ?)",
            products,
        )

    np.random.seed(42)
    start_date = datetime(2025, 9, 1)
    end_date = datetime(2026, 8, 31)
    num_days = (end_date - start_date).days
    transactions = []

    inventory_categories = ['Sales', 'Purchases']
    non_inventory_categories = ['Wages', 'Loan Repayment', 'Lending', 'Other Expenses', 'Capital', 'Other Income', 'Transportation', 'Maintenance']

    for day_offset in range(num_days + 1):
        current_date = start_date + timedelta(days=day_offset)
        date_str = current_date.strftime('%Y-%m-%d')

        if np.random.random() < 0.7:
            num_tx = np.random.poisson(1.5) + 1
            for _ in range(num_tx):
                category = np.random.choice(
                    inventory_categories + non_inventory_categories,
                    p=[0.40, 0.20] + [0.05] * len(non_inventory_categories),
                )
                if category in inventory_categories:
                    product_id = np.random.randint(1, len(products) + 1)
                    quantity = np.random.randint(1, 8) if category == 'Sales' else np.random.randint(5, 30)
                    amount = quantity * np.random.uniform(20, 80) if category == 'Sales' else quantity * np.random.uniform(15, 50)
                    product_id_value = product_id
                    quantity_value = quantity
                    description = None
                else:
                    product_id_value = None
                    quantity_value = 0
                    amount = round(np.random.uniform(50, 300), 2)
                    description = category

                flow_type = get_transaction_flow_type(category)
                transactions.append((
                    product_id_value,
                    category,
                    flow_type,
                    quantity_value,
                    round(amount, 2),
                    description,
                    date_str,
                ))

    with conn:
        cur = conn.cursor()
        if transactions:
            cur.executemany(
                "INSERT INTO transactions (product_id, category, flow_type, quantity, amount, description, date) VALUES (?, ?, ?, ?, ?, ?, ?)",
                transactions,
            )

    print(f"✓ Seeded {len(transactions)} transactions for the full year")
