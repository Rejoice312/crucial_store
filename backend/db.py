import sqlite3
from pathlib import Path
from config import debug
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

DB_PATH = Path(__file__).resolve().parent.parent / "crucial.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


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
        "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('products', 'transactions', 'expenses')"
    ).fetchall()
    return len(existing) == 3


def init_db() -> None:
    """Initialize DB if it doesn't exist; seed only if debug=True and there is no data."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not DB_PATH.exists():
        create_tables()
        if debug:
            _seed_sample_data()
        return

    conn = get_conn()
    if not _has_required_tables(conn):
        create_tables()

    if debug:
        product_count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if product_count == 0:
            _seed_sample_data()


def _seed_sample_data() -> None:
    """Seed full year of realistic sample data using numpy and pandas"""
    conn = get_conn()
    
    # Insert base products
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
    
    # Generate full year of transactions (2025-09-01 to 2026-08-31)
    np.random.seed(42)
    start_date = datetime(2025, 9, 1)
    end_date = datetime(2026, 8, 31)
    num_days = (end_date - start_date).days
    
    # Transaction data generation
    transactions = []
    for day_offset in range(num_days + 1):
        current_date = start_date + timedelta(days=day_offset)
        date_str = current_date.strftime('%Y-%m-%d')
        
        # 70% chance of at least one transaction per day
        if np.random.random() < 0.7:
            num_tx = np.random.poisson(1.5) + 1  # 1-3 transactions
            for _ in range(num_tx):
                product_id = np.random.randint(1, len(products) + 1)
                tx_type = np.random.choice(['Sales', 'Purchases'], p=[0.65, 0.35])
                
                if tx_type == 'Sales':
                    quantity = np.random.randint(1, 8)
                    amount = quantity * np.random.uniform(20, 80)
                else:
                    quantity = np.random.randint(5, 30)
                    amount = quantity * np.random.uniform(15, 50)
                
                transactions.append((product_id, quantity, round(amount, 2), tx_type, date_str))
    
    # Generate full year of expenses
    expenses = []
    for day_offset in range(num_days + 1):
        current_date = start_date + timedelta(days=day_offset)
        date_str = current_date.strftime('%Y-%m-%d')
        
        # 40% chance of expenses per day
        if np.random.random() < 0.4:
            num_exp = np.random.choice([1, 2], p=[0.7, 0.3])
            for _ in range(num_exp):
                category = np.random.choice(['Transportation', 'Charges'])
                if category == 'Transportation':
                    amount = round(np.random.uniform(30, 120), 2)
                else:
                    amount = round(np.random.uniform(10, 80), 2)
                
                expenses.append((category, amount, date_str))
    
    # Insert into database
    with conn:
        cur = conn.cursor()
        if transactions:
            cur.executemany(
                "INSERT INTO transactions (product_id, quantity, amount, type, date) VALUES (?, ?, ?, ?, ?)",
                transactions,
            )
        if expenses:
            cur.executemany(
                "INSERT INTO expenses (category, amount, date) VALUES (?, ?, ?)",
                expenses,
            )
    
    print(f"✓ Seeded {len(transactions)} transactions and {len(expenses)} expenses for full year")
