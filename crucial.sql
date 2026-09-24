PRAGMA foreign_keys=ON;

CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(20) NOT NULL,
    description VARCHAR(200),
    stock_qty INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    category TEXT NOT NULL CHECK(category IN ('Sales', 'Purchases', 'Wages', 'Loan Repayment', 'Lending', 'Other Expenses', 'Capital', 'Other Income', 'Transportation', 'Maintenance')),
    flow_type TEXT NOT NULL CHECK(flow_type IN ('Inflow', 'Outflow')),
    quantity INTEGER NOT NULL DEFAULT 0,
    amount REAL NOT NULL,
    description TEXT,
    date TEXT DEFAULT (DATE('now')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(product_id) REFERENCES products(id)
);
