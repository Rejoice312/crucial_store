from typing import List, Dict, Any, Optional
from .db import get_conn


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


def add_transaction(product_id: int, quantity: int, amount: float, ttype: str, date: str | None = None) -> int:
    if quantity <= 0:
        raise ValueError("invalid_quantity")
    if amount < 0:
        raise ValueError("invalid_amount")

    conn = get_conn()
    with conn:
        cur = conn.execute("SELECT stock_qty FROM products WHERE id=?", (product_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError("product_not_found")
        stock = row[0]
        if ttype == "Sales":
            if quantity > stock:
                raise ValueError("insufficient_stock")
            new_stock = stock - quantity
        elif ttype == "Purchases":
            new_stock = stock + quantity
        else:
            raise ValueError("invalid_type")

        conn.execute("UPDATE products SET stock_qty=? WHERE id=?", (new_stock, product_id))
        if date:
            cur2 = conn.execute(
                "INSERT INTO transactions (product_id, quantity, amount, type, date) VALUES (?, ?, ?, ?, ?)",
                (product_id, quantity, round(float(amount), 2), ttype, date),
            )
        else:
            cur2 = conn.execute(
                "INSERT INTO transactions (product_id, quantity, amount, type) VALUES (?, ?, ?, ?)",
                (product_id, quantity, round(float(amount), 2), ttype),
            )
        return cur2.lastrowid


def get_transactions() -> List[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.execute(
        "SELECT t.*, p.name as product_name FROM transactions t JOIN products p ON t.product_id=p.id ORDER BY t.date DESC, t.created_at DESC"
    )
    return [dict(r) for r in cur.fetchall()]


def delete_transaction(tx_id: int) -> None:
    conn = get_conn()
    with conn:
        cur = conn.execute("SELECT product_id, quantity, type FROM transactions WHERE id=?", (tx_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError("tx_not_found")
        pid, qty, ttype = row[0], row[1], row[2]
        cur = conn.execute("SELECT stock_qty FROM products WHERE id=?", (pid,))
        p = cur.fetchone()
        if p:
            stock = p[0]
            if ttype == 'Sales':
                new_stock = stock + qty
            else:
                new_stock = stock - qty
            conn.execute("UPDATE products SET stock_qty=? WHERE id=?", (new_stock, pid))
        conn.execute("DELETE FROM transactions WHERE id=?", (tx_id,))


def add_expense(category: str, amount: float) -> int:
    if category not in {'Transportation', 'Charges'}:
        raise ValueError("invalid_category")
    if amount < 0:
        raise ValueError("invalid_amount")
    conn = get_conn()
    with conn:
        cur = conn.execute(
            "INSERT INTO expenses (category, amount) VALUES (?, ?)", (category, round(float(amount), 2))
        )
        return cur.lastrowid


def add_expense_with_date(category: str, amount: float, date: str | None = None) -> int:
    if category not in {'Transportation', 'Charges'}:
        raise ValueError("invalid_category")
    if amount < 0:
        raise ValueError("invalid_amount")
    conn = get_conn()
    with conn:
        if date:
            cur = conn.execute(
                "INSERT INTO expenses (category, amount, date) VALUES (?, ?, ?)", (category, round(float(amount), 2), date)
            )
        else:
            cur = conn.execute(
                "INSERT INTO expenses (category, amount) VALUES (?, ?)", (category, round(float(amount), 2))
            )
        return cur.lastrowid


def delete_expense(expense_id: int) -> None:
    conn = get_conn()
    with conn:
        conn.execute("DELETE FROM expenses WHERE id=?", (expense_id,))


def get_expenses() -> List[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.execute("SELECT * FROM expenses ORDER BY created_at DESC")
    return [dict(r) for r in cur.fetchall()]


def get_kpis() -> Dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT SUM(CASE WHEN type='Sales' THEN amount ELSE 0 END) as total_sales, SUM(CASE WHEN type='Purchases' THEN amount ELSE 0 END) as total_purchases FROM transactions")
    totals = cur.fetchone()
    cur.execute("SELECT SUM(amount) FROM expenses")
    total_expenses = cur.fetchone()[0] or 0
    cur.execute("SELECT SUM(stock_qty) FROM products")
    total_stock = cur.fetchone()[0] or 0
    return {
        "total_sales": round(totals[0] or 0, 2),
        "total_purchases": round(totals[1] or 0, 2),
        "total_expenses": round(total_expenses, 2),
        "total_stock_qty": total_stock,
    }
