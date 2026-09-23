import streamlit as st
from pathlib import Path
from backend.db import init_db
from backend import crud
import pandas as pd
import plotly.express as px


def friendly_label(value):
    if value is None:
        return ""
    text = str(value).replace("_", " ").replace("-", " ")
    return " ".join(part.capitalize() for part in text.split())


def chart_df_from_tx(df_tx):
    if df_tx.empty:
        return df_tx
    return df_tx.rename(columns={
        "product_name": "Product Name",
        "quantity": "Quantity",
        "amount": "Amount",
        "type": "Type",
        "date": "Date",
        "id": "Id",
    })


def chart_df_from_exp(df_exp):
    if df_exp.empty:
        return df_exp
    return df_exp.rename(columns={
        "category": "Category",
        "amount": "Amount",
        "date": "Date",
        "id": "Id",
    })


def apply_dark_theme_to_fig(fig):
    fig.update_layout(
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117",
        font=dict(color="#F3F4F6", family="Poppins, Segoe UI, sans-serif"),
        title_font=dict(color="#F3F4F6", size=18),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1.0, font=dict(color="#9CA3AF")),
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis=dict(
            gridcolor="#2D3748",
            zerolinecolor="#2D3748",
            tickfont=dict(color="#9CA3AF"),
            title=dict(text="", font=dict(color="#F3F4F6")),
        ),
        yaxis=dict(
            gridcolor="#2D3748",
            zerolinecolor="#2D3748",
            tickfont=dict(color="#9CA3AF"),
            title=dict(text="", font=dict(color="#F3F4F6")),
        ),
        coloraxis_colorbar=dict(title=dict(font=dict(color="#F3F4F6")), tickfont=dict(color="#9CA3AF")),
    )
    return fig


def money(value):
    try:
        return f"₦{float(value):,.2f}"
    except (TypeError, ValueError):
        return "₦0.00"


def get_period_range():
    txs = crud.get_transactions()
    exps = crud.get_expenses()
    dates = []
    for row in txs:
        if row.get('date'):
            dates.append(pd.to_datetime(row['date']).date())
    for row in exps:
        if row.get('date'):
            dates.append(pd.to_datetime(row['date']).date())

    today = pd.Timestamp.today().date()
    one_month_ago = (pd.Timestamp.today() - pd.DateOffset(months=1)).date()

    if not dates:
        return one_month_ago, today

    min_date = min(dates)
    max_date = max(dates)

    default_start = max(min_date, one_month_ago)
    default_end = min(max_date, today)

    if default_end < default_start:
        default_start, default_end = default_end, default_start

    return default_start, default_end


def filter_by_period(dataframe, start_date, end_date, date_col='date'):
    if dataframe.empty:
        return dataframe
    df = dataframe.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    return df[(df[date_col].dt.date >= start_date) & (df[date_col].dt.date <= end_date)].copy()


def dashboard():
    period_start, period_end = get_period_range()
    st.sidebar.caption("Dashboard period")
    start_date = st.sidebar.date_input(
        "Start date",
        value=period_start,
        min_value=period_start,
        max_value=period_end,
    )
    end_date = st.sidebar.date_input(
        "End date",
        value=period_end,
        min_value=period_start,
        max_value=period_end,
    )

    if end_date < start_date:
        start_date, end_date = end_date, start_date

    period_start = start_date
    period_end = end_date

    txs = crud.get_transactions()
    exps = crud.get_expenses()
    prods = crud.get_products()

    if txs:
        df_tx = pd.DataFrame(txs)
        df_tx['date'] = pd.to_datetime(df_tx['date'])
    else:
        df_tx = pd.DataFrame(columns=["id", "product_id", "quantity", "amount", "type", "date", "created_at", "product_name"])

    if exps:
        df_exp = pd.DataFrame(exps)
        df_exp['date'] = pd.to_datetime(df_exp['date'])
    else:
        df_exp = pd.DataFrame(columns=["id", "category", "amount", "date", "created_at"])

    df_tx = filter_by_period(df_tx, period_start, period_end)
    df_exp = filter_by_period(df_exp, period_start, period_end)

    sales_total = float(df_tx.loc[df_tx['type'] == 'Sales', 'amount'].sum()) if not df_tx.empty else 0.0
    purchases_total = float(df_tx.loc[df_tx['type'] == 'Purchases', 'amount'].sum()) if not df_tx.empty else 0.0
    expenses_total = float(df_exp['amount'].sum()) if not df_exp.empty else 0.0
    stock_total = sum(int(p['stock_qty']) for p in prods) if prods else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(f"<div class='kpi-card card'><div class='kpi-title'>Total Sales</div><div class='kpi-value'>{money(sales_total)}</div></div>", unsafe_allow_html=True)
    k2.markdown(f"<div class='kpi-card card'><div class='kpi-title'>Total Purchases</div><div class='kpi-value'>{money(purchases_total)}</div></div>", unsafe_allow_html=True)
    k3.markdown(f"<div class='kpi-card card'><div class='kpi-title'>Total Expenses</div><div class='kpi-value'>{money(expenses_total)}</div></div>", unsafe_allow_html=True)
    k4.markdown(f"<div class='kpi-card card'><div class='kpi-title'>Stock Qty</div><div class='kpi-value'>{stock_total}</div></div>", unsafe_allow_html=True)

    df_prods = pd.DataFrame(prods) if prods else pd.DataFrame(columns=["id", "name", "description", "stock_qty"])

    st.subheader("Charts & Trends")
    left, right = st.columns([2, 1])
    palette = px.colors.qualitative.Set3

    if not df_tx.empty:
        sales_ts = df_tx[df_tx['type'] == 'Sales'].groupby(df_tx['date'].dt.date).agg({'amount': 'sum'}).reset_index()
        sales_ts.columns = ['Date', 'Amount']
        fig1 = px.line(sales_ts, x='Date', y='Amount', title='Sales Over Time', markers=True)
        fig1.update_traces(line=dict(color=palette[0]), marker=dict(color=palette[1]))
        fig1.update_xaxes(title_text='Date')
        fig1.update_yaxes(title_text='Sales Amount (₦)')
        apply_dark_theme_to_fig(fig1)
        left.plotly_chart(fig1, use_container_width=True)

    if not df_tx.empty:
        pur_ts = df_tx[df_tx['type'] == 'Purchases'].groupby(df_tx['date'].dt.date).agg({'amount': 'sum'}).reset_index()
        pur_ts.columns = ['Date', 'Amount']
        fig2 = px.line(pur_ts, x='Date', y='Amount', title='Purchases Over Time', markers=True)
        fig2.update_traces(line=dict(color=palette[2]), marker=dict(color=palette[3]))
        fig2.update_xaxes(title_text='Date')
        fig2.update_yaxes(title_text='Purchase Amount (₦)')
        apply_dark_theme_to_fig(fig2)
        left.plotly_chart(fig2, use_container_width=True)

    if not df_tx.empty:
        top_prods = df_tx[df_tx['type'] == 'Sales'].groupby('product_name').agg({'quantity': 'sum'}).reset_index().sort_values('quantity', ascending=False).head(10)
        top_prods.columns = ['Product Name', 'Units Sold']
        if not top_prods.empty:
            fig4 = px.bar(top_prods, x='Product Name', y='Units Sold', title='Top Products by Units Sold', color='Product Name', color_discrete_sequence=palette)
            fig4.update_xaxes(title_text='Product Name')
            fig4.update_yaxes(title_text='Units Sold')
            apply_dark_theme_to_fig(fig4)
            left.plotly_chart(fig4, use_container_width=True)

    if not df_exp.empty:
        exp_ts = df_exp.groupby(df_exp['date'].dt.date).agg({'amount': 'sum'}).reset_index()
        exp_ts.columns = ['Date', 'Amount']
        fig3 = px.area(exp_ts, x='Date', y='Amount', title='Expenses Over Time')
        fig3.update_traces(line=dict(color=palette[4]))
        fig3.update_xaxes(title_text='Date')
        fig3.update_yaxes(title_text='Expense Amount (₦)')
        apply_dark_theme_to_fig(fig3)
        right.plotly_chart(fig3, use_container_width=True)

        exp_cat = df_exp.groupby('category').agg({'amount': 'sum'}).reset_index()
        exp_cat.columns = ['Category', 'Amount']
        fig3b = px.pie(exp_cat, names='Category', values='Amount', title='Expenses by Category', color_discrete_sequence=palette)
        fig3b.update_traces(textinfo='percent+label')
        apply_dark_theme_to_fig(fig3b)
        right.plotly_chart(fig3b, use_container_width=True)

    if not df_tx.empty or not df_exp.empty:
        daily = []
        start_day = min(pd.Timestamp(period_start), pd.Timestamp(period_end))
        end_day = max(pd.Timestamp(period_start), pd.Timestamp(period_end))
        date_range = pd.date_range(start=start_day, end=end_day, freq='D')
        for d in date_range:
            ds = d.strftime('%Y-%m-%d')
            sales_amt = float(df_tx[(df_tx['type'] == 'Sales') & (df_tx['date'].dt.strftime('%Y-%m-%d') == ds)]['amount'].sum()) if not df_tx.empty else 0.0
            purchase_amt = float(df_tx[(df_tx['type'] == 'Purchases') & (df_tx['date'].dt.strftime('%Y-%m-%d') == ds)]['amount'].sum()) if not df_tx.empty else 0.0
            expense_amt = float(df_exp[(df_exp['date'].dt.strftime('%Y-%m-%d') == ds)]['amount'].sum()) if not df_exp.empty else 0.0
            net_balance = sales_amt - purchase_amt - expense_amt
            daily.append({'Date': ds, 'Net Balance': net_balance})

        if daily:
            net_df = pd.DataFrame(daily)
            net_df['Date'] = pd.to_datetime(net_df['Date'])
            st.subheader('Net Balance Over Time')
            fig_net = px.line(net_df, x='Date', y='Net Balance', title='Business Net Balance Over Time', markers=True)
            fig_net.update_traces(line=dict(color=palette[5]), marker=dict(color=palette[1]))
            fig_net.update_xaxes(title_text='Date')
            fig_net.update_yaxes(title_text='Net Balance (₦)')
            apply_dark_theme_to_fig(fig_net)
            st.plotly_chart(fig_net, use_container_width=True)

    if not df_prods.empty:
        stock_df = df_prods[['name', 'stock_qty']].copy()
        stock_df.columns = ['Product Name', 'Stock Quantity']
        st.subheader('Inventory')
        fig5 = px.bar(stock_df, x='Product Name', y='Stock Quantity', title='Current Stock Levels', color='Product Name', color_discrete_sequence=palette)
        fig5.update_xaxes(title_text='Product Name')
        fig5.update_yaxes(title_text='Stock Quantity')
        apply_dark_theme_to_fig(fig5)
        st.plotly_chart(fig5, use_container_width=True)

    st.subheader("Recent Transactions")
    if not df_tx.empty:
        recent = df_tx[['id', 'product_name', 'quantity', 'amount', 'type', 'date']].copy()
        recent.columns = ['Id', 'Product', 'Quantity', 'Amount', 'Type', 'Date']
        recent['Amount'] = recent['Amount'].map(lambda v: money(v))
        st.dataframe(recent.sort_values('Date', ascending=False).head(10), use_container_width=True, hide_index=True)
    else:
        st.info("No transactions for the selected period.")

    if not df_exp.empty:
        exp_display = df_exp[['id', 'category', 'amount', 'date']].copy()
        exp_display.columns = ['Id', 'Category', 'Amount', 'Date']
        exp_display['Amount'] = exp_display['Amount'].map(lambda v: money(v))
        st.dataframe(exp_display.sort_values('Date', ascending=False).head(10), use_container_width=True, hide_index=True)


def products_page():
    st.header("Products")
    with st.expander("Add product"):
        with st.form("add_prod"):
            name = st.text_input("Name", max_chars=20)
            desc = st.text_area("Description", max_chars=200)
            qty = st.number_input("Stock quantity", min_value=0, value=0)
            submitted = st.form_submit_button("Add")
            if submitted:
                if not name:
                    st.error("Name required")
                else:
                    crud.add_product(name, desc, int(qty))
                    st.success("Product added")
                    st.rerun()

    prods = crud.get_products()
    search_term = st.text_input("Search products", placeholder="Search by name or description")
    filtered = []
    for p in prods:
        haystack = f"{p['name']} {p['description'] or ''}".lower()
        if search_term.lower() in haystack:
            filtered.append(p)

    if not filtered:
        st.info("No products match your search.")
        return

    product_df = pd.DataFrame(filtered)
    product_df = product_df[['id', 'name', 'description', 'stock_qty']].copy()
    product_df.columns = ['Id', 'Name', 'Description', 'Stock Quantity']
    st.dataframe(product_df, use_container_width=True, hide_index=True)

    cols = st.columns(3)
    for idx, p in enumerate(filtered[:3]):
        with cols[idx % 3].container():
            st.markdown(f"<div class='card'><b>{p['name']}</b><br>{p['description'] or 'No description'}<br><small>Stock: {p['stock_qty']}</small></div>", unsafe_allow_html=True)
            row_col1, row_col2 = st.columns(2)
            if row_col1.button("Edit", key=f"edit-prod-{p['id']}"):
                st.session_state['product_edit_id'] = p['id']
            if row_col2.button("Delete", key=f"del-prod-{p['id']}"):
                crud.delete_product(p['id'])
                st.success(f"Deleted product {p['name']}")
                st.rerun()

    if 'product_edit_id' in st.session_state:
        edit_id = st.session_state['product_edit_id']
        product = crud.get_product_by_id(edit_id)
        if product:
            with st.form(f"edit-product-{edit_id}"):
                st.subheader(f"Edit product: {product['name']}")
                nn = st.text_input("Name", value=product['name'])
                dd = st.text_area("Description", value=product['description'] or "")
                qq = st.number_input("Stock quantity", min_value=0, value=product['stock_qty'])
                ok = st.form_submit_button("Update")
                if ok:
                    crud.update_product(edit_id, nn, dd, int(qq))
                    st.success("Updated product")
                    del st.session_state['product_edit_id']
                    st.rerun()


def transactions_page():
    st.header("Transactions")
    prods = crud.get_products()
    if not prods:
        st.warning("No products exist yet. Add a product before creating a transaction.")
        return

    with st.expander("Add transaction"):
        prod_map = {p['name']: p['id'] for p in prods}
        with st.form("add_tx"):
            psel = st.selectbox("Product", options=[p['name'] for p in prods])
            ttype = st.selectbox("Type", ["Sales", "Purchases"])
            qty = st.number_input("Quantity", min_value=1, value=1)
            amt = st.number_input("Amount", min_value=0.0, format="%.2f")
            date = st.date_input("Date")
            ok = st.form_submit_button("Add Transaction")
            if ok:
                pid = prod_map.get(psel)
                try:
                    crud.add_transaction(pid, int(qty), float(amt), ttype, date.isoformat())
                    st.success("Transaction added")
                    st.rerun()
                except ValueError as e:
                    if str(e) == 'product_not_found':
                        st.error("Selected product not found")
                    elif str(e) == 'insufficient_stock':
                        st.error("Insufficient stock for sale")
                    else:
                        st.error("Error adding transaction")

    st.subheader("All Transactions")
    txs = crud.get_transactions()
    search_term = st.text_input("Search transactions", placeholder="Search product, type, date")
    tx_table = pd.DataFrame(txs)
    if tx_table.empty:
        st.info("No transactions yet")
        return
    tx_table['date'] = pd.to_datetime(tx_table['date'])
    if search_term:
        tx_table = tx_table[tx_table.astype(str).apply(lambda col: col.str.contains(search_term, case=False, na=False)).any(axis=1)]
    tx_table = tx_table[['id', 'product_name', 'quantity', 'amount', 'type', 'date']].copy()
    tx_table.columns = ['Id', 'Product', 'Quantity', 'Amount', 'Type', 'Date']
    st.dataframe(tx_table.sort_values('Date', ascending=False), use_container_width=True, hide_index=True)

    for t in txs:
        if search_term and search_term.lower() not in f"{t['product_name']} {t['type']} {t['date']}".lower():
            continue
        cols = st.columns([2, 1, 1, 1, 1, 1])
        cols[0].write(f"{t['date']} — {t['product_name']}")
        cols[1].write(f"{t['type']}")
        cols[2].write(f"Qty: {t['quantity']}")
        cols[3].write(f"₦{t['amount']:,.2f}")
        if cols[4].button("Delete", key=f"del_tx_{t['id']}"):
            try:
                crud.delete_transaction(t['id'])
                st.success("Transaction deleted and stock updated")
                st.rerun()
            except Exception:
                st.error("Failed to delete transaction")


def expenses_page():
    st.header("Expenses")
    with st.expander("Add expense"):
        with st.form("add_exp"):
            cat = st.selectbox("Category", ["Transportation", "Charges"])
            amt = st.number_input("Amount", min_value=0.0, format="%.2f")
            date = st.date_input("Date")
            ok = st.form_submit_button("Add Expense")
            if ok:
                crud.add_expense_with_date(cat, float(amt), date.isoformat())
                st.success("Expense added")
                st.rerun()

    ex = crud.get_expenses()
    search_term = st.text_input("Search expenses", placeholder="Search category or amount")
    ex_df = pd.DataFrame(ex)
    if not ex_df.empty:
        ex_df['date'] = pd.to_datetime(ex_df['date'])
        if search_term:
            ex_df = ex_df[ex_df.astype(str).apply(lambda col: col.str.contains(search_term, case=False, na=False)).any(axis=1)]
        ex_df = ex_df[['id', 'category', 'amount', 'date']].copy()
        ex_df.columns = ['Id', 'Category', 'Amount', 'Date']
        st.dataframe(ex_df.sort_values('Date', ascending=False), use_container_width=True, hide_index=True)

    if ex:
        for e in ex:
            if search_term and search_term.lower() not in f"{e['category']} {e['amount']} {e['date']}".lower():
                continue
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"{e['date']} — {e['category']}: ₦{e['amount']:,.2f}")
            if c2.button("Delete", key=f"del_exp_{e['id']}"):
                try:
                    crud.delete_expense(e['id'])
                    st.success("Expense deleted")
                    st.rerun()
                except Exception:
                    st.error("Failed to delete expense")
    else:
        st.info("No expenses yet")


def main():
    init_db()
    st.set_page_config(page_title="Crucial Clothing Store", layout="wide")

    style_path = Path(__file__).resolve().parent / "styles.css"
    with open(style_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    header_html = '''
    <div class="header">
        <div class="logo-badge">
            <div class="logo-mark">CC</div>
            <div class="brand-text">
                <div class="brand-title">Crucial Clothing Store</div>
                <div class="brand-sub">Business Manager</div>
            </div>
        </div>
        <div class="brand-sub">Beautiful analytics & inventory</div>
    </div>
    '''
    st.markdown(header_html, unsafe_allow_html=True)
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    PAGES = ["Dashboard", "Products", "Transactions", "Expenses"]
    page = st.sidebar.selectbox("Navigate", PAGES)

    if page == "Dashboard":
        dashboard()
    elif page == "Products":
        products_page()
    elif page == "Transactions":
        transactions_page()
    elif page == "Expenses":
        expenses_page()


if __name__ == "__main__":
    main()
