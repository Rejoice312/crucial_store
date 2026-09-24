from typing import List, Dict, Any, Optional
from .db import get_conn

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


def get_transaction_flow_type(category: str) -> str:
    normalized_category = (category or '').strip()
    if normalized_category not in VALID_TRANSACTION_CATEGORIES:
        raise ValueError("invalid_category")
    return "Inflow" if normalized_category in INFLOW_TRANSACTION_CATEGORIES else "Outflow"


def add_product(name: str, description: Optional[str], stock_qty: int) -> int:
    if not name or not name.strip():
        raise ValueError("name_required")
    if stock_qty < 0:
        raise ValueError("invalid_stock")

    conn = get_conn()
    with conn:
        cur = conn.execute(
            "INSERT INTO products (name, description, stock_qty) VALUES (?, ?, ?)",
            (name.strip()[:20], description[:200] if description else None, stock_qty),
        )
        return cur.lastrowid


def update_product(product_id: int, name: str, description: Optional[str], stock_qty: int) -> None:
    if not name or not name.strip():
        raise ValueError("name_required")
    if stock_qty < 0:
        raise ValueError("invalid_stock")

    conn = get_conn()
    with conn:
        conn.execute(
            "UPDATE products SET name=?, description=?, stock_qty=? WHERE id=?",
            (name.strip()[:20], description[:200] if description else None, stock_qty, product_id),
        )


def delete_product(product_id: int) -> None:
    conn = get_conn()
    with conn:
        conn.execute("DELETE FROM transactions WHERE product_id=?", (product_id,))
        conn.execute("DELETE FROM products WHERE id=?", (product_id,))


def get_products() -> List[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.execute("SELECT * FROM products ORDER BY id DESC")
    return [dict(r) for r in cur.fetchall()]


def get_product_by_id(product_id: int) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.execute("SELECT * FROM products WHERE id=?", (product_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def add_transaction(
    product_id: Optional[int],
    quantity: int,
    amount: float,
    category: str,
    description: Optional[str] = None,
    date: str | None = None,
) -> int:
    normalized_category = (category or '').strip()
    if normalized_category not in VALID_TRANSACTION_CATEGORIES:
        raise ValueError("invalid_category")
    if amount < 0:
        raise ValueError("invalid_amount")

    flow_type = get_transaction_flow_type(normalized_category)
    normalized_quantity = int(quantity or 0)

    if normalized_category in {'Sales', 'Purchases'}:
        if product_id is None:
            raise ValueError("product_required")
        if normalized_quantity <= 0:
            raise ValueError("invalid_quantity")
    elif product_id is not None and normalized_quantity < 0:
        raise ValueError("invalid_quantity")

    conn = get_conn()
    with conn:
        if product_id is not None:
            row = conn.execute("SELECT stock_qty FROM products WHERE id=?", (product_id,)).fetchone()
            if not row:
                raise ValueError("product_not_found")
            stock = int(row[0])

            if normalized_category == 'Sales':
                if normalized_quantity > stock:
                    raise ValueError("insufficient_stock")
                new_stock = stock - normalized_quantity
            elif normalized_category == 'Purchases':
                new_stock = stock + normalized_quantity
            else:
                new_stock = stock

            conn.execute("UPDATE products SET stock_qty=? WHERE id=?", (new_stock, product_id))

        if description:
            description_text = description.strip()[:200]
        else:
            description_text = None

        if date:
            cur = conn.execute(
                "INSERT INTO transactions (product_id, category, flow_type, quantity, amount, description, date) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (product_id, normalized_category, flow_type, normalized_quantity, round(float(amount), 2), description_text, date),
            )
        else:
            cur = conn.execute(
                "INSERT INTO transactions (product_id, category, flow_type, quantity, amount, description) VALUES (?, ?, ?, ?, ?, ?)",
                (product_id, normalized_category, flow_type, normalized_quantity, round(float(amount), 2), description_text),
            )
        return cur.lastrowid


def get_transactions() -> List[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.execute(
        "SELECT t.*, p.name as product_name FROM transactions t LEFT JOIN products p ON t.product_id = p.id ORDER BY t.date DESC, t.created_at DESC"
    )
    return [dict(r) for r in cur.fetchall()]


def delete_transaction(tx_id: int) -> None:
    conn = get_conn()
    with conn:
        cur = conn.execute("SELECT product_id, quantity, category FROM transactions WHERE id=?", (tx_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError("tx_not_found")

        pid, qty, category = row[0], row[1], row[2]
        if pid is not None:
            stock_row = conn.execute("SELECT stock_qty FROM products WHERE id=?", (pid,)).fetchone()
            if stock_row:
                stock = int(stock_row[0])
                if category == 'Sales':
                    new_stock = stock + qty
                elif category == 'Purchases':
                    new_stock = stock - qty
                else:
                    new_stock = stock
                conn.execute("UPDATE products SET stock_qty=? WHERE id=?", (new_stock, pid))

        conn.execute("DELETE FROM transactions WHERE id=?", (tx_id,))


def get_kpis() -> Dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            SUM(CASE WHEN category='Sales' THEN amount ELSE 0 END) as total_sales,
            SUM(CASE WHEN category='Purchases' THEN amount ELSE 0 END) as total_purchases,
            SUM(CASE WHEN flow_type='Inflow' THEN amount ELSE 0 END) as total_inflow,
            SUM(CASE WHEN flow_type='Outflow' THEN amount ELSE 0 END) as total_outflow
        FROM transactions
        """
    )
    totals = cur.fetchone()
    cur.execute("SELECT SUM(stock_qty) FROM products")
    total_stock = cur.fetchone()[0] or 0

    return {
        "total_sales": round(totals[0] or 0, 2),
        "total_purchases": round(totals[1] or 0, 2),
        "total_inflow": round(totals[2] or 0, 2),
        "total_outflow": round(totals[3] or 0, 2),
        "total_stock_qty": total_stock,
    }
