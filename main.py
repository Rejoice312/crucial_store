import streamlit as st
from pathlib import Path
from datetime import date
import pandas as pd
import plotly.express as px

from backend.db import init_db
from backend import crud


def friendly_label(value):
    if value is None:
        return ""
    text = str(value).replace("_", " ").replace("-", " ")
    return " ".join(part.capitalize() for part in text.split())


def money(value):
    try:
        return f"₦{float(value):,.2f}"
    except (TypeError, ValueError):
        return "₦0.00"


def get_period_range():
    txs = crud.get_transactions()
    dates = []
    for row in txs:
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

    txs = crud.get_transactions()
    prods = crud.get_products()

    if txs:
        df_tx = pd.DataFrame(txs)
        df_tx['date'] = pd.to_datetime(df_tx['date'])
    else:
        df_tx = pd.DataFrame(columns=[
            'id', 'product_id', 'category', 'flow_type', 'quantity', 'amount', 'description', 'date', 'created_at', 'product_name'
        ])

    df_tx = filter_by_period(df_tx, start_date, end_date)
    sales_total = float(df_tx.loc[df_tx['category'] == 'Sales', 'amount'].sum()) if not df_tx.empty else 0.0
    purchases_total = float(df_tx.loc[df_tx['category'] == 'Purchases', 'amount'].sum()) if not df_tx.empty else 0.0
    inflow_total = float(df_tx.loc[df_tx['flow_type'] == 'Inflow', 'amount'].sum()) if not df_tx.empty else 0.0
    outflow_total = float(df_tx.loc[df_tx['flow_type'] == 'Outflow', 'amount'].sum()) if not df_tx.empty else 0.0
    stock_total = sum(int(p['stock_qty']) for p in prods) if prods else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(f"<div class='kpi-card card'><div class='kpi-title'>Total Sales</div><div class='kpi-value'>{money(sales_total)}</div></div>", unsafe_allow_html=True)
    k2.markdown(f"<div class='kpi-card card'><div class='kpi-title'>Total Purchases</div><div class='kpi-value'>{money(purchases_total)}</div></div>", unsafe_allow_html=True)
    k3.markdown(f"<div class='kpi-card card'><div class='kpi-title'>Total Outflow</div><div class='kpi-value'>{money(outflow_total)}</div></div>", unsafe_allow_html=True)
    k4.markdown(f"<div class='kpi-card card'><div class='kpi-title'>Stock Qty</div><div class='kpi-value'>{stock_total}</div></div>", unsafe_allow_html=True)

    if not df_tx.empty:
        st.subheader("Transaction Mix")
        left, right = st.columns([2, 1])
        palette = px.colors.qualitative.Set3

        sales_ts = df_tx[df_tx['category'] == 'Sales'].groupby(df_tx['date'].dt.date).agg({'amount': 'sum'}).reset_index()
        sales_ts.columns = ['Date', 'Amount']
        if not sales_ts.empty:
            fig_sales = px.line(sales_ts, x='Date', y='Amount', title='Sales Over Time', markers=True)
            fig_sales.update_traces(line=dict(color=palette[0]), marker=dict(color=palette[1]))
            fig_sales.update_xaxes(title_text='Date')
            fig_sales.update_yaxes(title_text='Sales Amount (₦)')
            left.plotly_chart(fig_sales, use_container_width=True)

        category_summary = df_tx.groupby('category').agg({'amount': 'sum'}).reset_index()
        category_summary.columns = ['Category', 'Amount']
        if not category_summary.empty:
            fig_category = px.pie(category_summary, names='Category', values='Amount', title='Transactions by Category', color_discrete_sequence=palette)
            fig_category.update_traces(textinfo='percent+label')
            right.plotly_chart(fig_category, use_container_width=True)

        net_df = df_tx.groupby(df_tx['date'].dt.date).agg({'amount': 'sum'}).reset_index()
        net_df.columns = ['Date', 'Net Amount']
        if not net_df.empty:
            fig_net = px.line(net_df, x='Date', y='Net Amount', title='Daily Cash Movement', markers=True)
            fig_net.update_traces(line=dict(color=palette[5]), marker=dict(color=palette[2]))
            fig_net.update_xaxes(title_text='Date')
            fig_net.update_yaxes(title_text='Amount (₦)')
            st.plotly_chart(fig_net, use_container_width=True)

    df_prods = pd.DataFrame(prods) if prods else pd.DataFrame(columns=['id', 'name', 'description', 'stock_qty'])
    if not df_prods.empty:
        stock_df = df_prods[['name', 'stock_qty']].copy()
        stock_df.columns = ['Product Name', 'Stock Quantity']
        st.subheader('Inventory')
        fig5 = px.bar(stock_df, x='Product Name', y='Stock Quantity', title='Current Stock Levels', color='Product Name', color_discrete_sequence=px.colors.qualitative.Set3)
        fig5.update_xaxes(title_text='Product Name')
        fig5.update_yaxes(title_text='Stock Quantity')
        st.plotly_chart(fig5, use_container_width=True)

    st.subheader('Recent Transactions')
    if df_tx.empty:
        st.info('No transactions for the selected period.')
    else:
        recent = df_tx[['id', 'product_name', 'category', 'flow_type', 'quantity', 'amount', 'date']].copy()
        recent.columns = ['Id', 'Product', 'Category', 'Flow Type', 'Quantity', 'Amount', 'Date']
        recent['Amount'] = recent['Amount'].map(lambda v: money(v))
        st.dataframe(recent.sort_values('Date', ascending=False).head(10), use_container_width=True, hide_index=True)


def products_page():
    st.header('Products')
    with st.expander('Add product'):
        with st.form('add_prod'):
            name = st.text_input('Name', max_chars=20)
            desc = st.text_area('Description', max_chars=200)
            qty = st.number_input('Stock quantity', min_value=0, value=0)
            submitted = st.form_submit_button('Add')
            if submitted:
                if not name:
                    st.error('Name required')
                else:
                    crud.add_product(name, desc, int(qty))
                    st.success('Product added')
                    st.rerun()

    prods = crud.get_products()
    search_term = st.text_input('Search products', placeholder='Search by name or description')
    filtered = []
    for p in prods:
        haystack = f"{p['name']} {p['description'] or ''}".lower()
        if search_term.lower() in haystack:
            filtered.append(p)

    if not filtered:
        st.info('No products match your search.')
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
            if row_col1.button('Edit', key=f'edit-prod-{p["id"]}'):
                st.session_state['product_edit_id'] = p['id']
            if row_col2.button('Delete', key=f'del-prod-{p["id"]}'):
                crud.delete_product(p['id'])
                st.success(f'Deleted product {p["name"]}')
                st.rerun()

    if 'product_edit_id' in st.session_state:
        edit_id = st.session_state['product_edit_id']
        product = crud.get_product_by_id(edit_id)
        if product:
            with st.form(f'edit-product-{edit_id}'):
                st.subheader(f'Edit product: {product["name"]}')
                nn = st.text_input('Name', value=product['name'])
                dd = st.text_area('Description', value=product['description'] or '')
                qq = st.number_input('Stock quantity', min_value=0, value=product['stock_qty'])
                ok = st.form_submit_button('Update')
                if ok:
                    crud.update_product(edit_id, nn, dd, int(qq))
                    st.success('Updated product')
                    del st.session_state['product_edit_id']
                    st.rerun()


def transactions_page():
    st.header('Transactions')
    prods = crud.get_products()

    if 'tx_step' not in st.session_state:
        st.session_state.tx_step = 'basic'
    if 'pending_category' not in st.session_state:
        st.session_state.pending_category = None
    if 'pending_amount' not in st.session_state:
        st.session_state.pending_amount = 0.0
    if 'pending_date' not in st.session_state:
        st.session_state.pending_date = date.today().isoformat()

    with st.expander('Add transaction'):
        if st.session_state.tx_step == 'basic':
            with st.form('add_tx_basic'):
                category = st.selectbox('Category', options=sorted(crud.VALID_TRANSACTION_CATEGORIES), key='tx_basic_category')
                amount = st.number_input('Amount', min_value=0.0, format='%.2f', key='tx_basic_amount')
                date_value = st.date_input('Date', key='tx_basic_date')

                submitted = st.form_submit_button('Continue')
                if submitted:
                    if category in {'Sales', 'Purchases'}:
                        st.session_state.pending_category = category
                        st.session_state.pending_amount = float(amount)
                        st.session_state.pending_date = date_value.isoformat()
                        st.session_state.tx_step = 'inventory'
                        st.rerun()
                    else:
                        try:
                            crud.add_transaction(None, 0, float(amount), category, date=date_value.isoformat())
                            st.success('Transaction added')
                            st.session_state.tx_step = 'basic'
                            st.rerun()
                        except ValueError as exc:
                            st.error(f'Error adding transaction: {exc}')

        elif st.session_state.tx_step == 'inventory':
            with st.form('add_tx_inventory'):
                if not prods:
                    st.warning('Create a product before adding a sale or purchase.')
                    st.form_submit_button('Back', on_click=lambda: st.session_state.__setitem__('tx_step', 'basic'))
                else:
                    psel = st.selectbox('Product', options=[p['name'] for p in prods], index=0, key='tx_inventory_product')
                    qty = st.number_input('Quantity', min_value=1, value=1, key='tx_inventory_quantity')

                    row = st.columns(2)
                    if row[0].form_submit_button('Back'):
                        st.session_state.tx_step = 'basic'
                        st.rerun()
                    if row[1].form_submit_button('Save Transaction'):
                        pid = next(p['id'] for p in prods if p['name'] == psel)
                        try:
                            crud.add_transaction(
                                pid,
                                int(qty),
                                float(st.session_state.pending_amount),
                                st.session_state.pending_category,
                                date=st.session_state.pending_date,
                            )
                            st.success('Transaction added')
                            st.session_state.tx_step = 'basic'
                            st.rerun()
                        except ValueError as exc:
                            if str(exc) == 'product_not_found':
                                st.error('Selected product not found')
                            elif str(exc) == 'insufficient_stock':
                                st.error('Insufficient stock for this sale')
                            else:
                                st.error(f'Error adding transaction: {exc}')


    st.subheader('All Transactions')
    txs = crud.get_transactions()
    search_term = st.text_input('Search transactions', placeholder='Search product, category, flow type, date')
    tx_table = pd.DataFrame(txs)
    if tx_table.empty:
        st.info('No transactions yet')
        return

    tx_table['date'] = pd.to_datetime(tx_table['date'])
    if search_term:
        tx_table = tx_table[tx_table.astype(str).apply(lambda col: col.str.contains(search_term, case=False, na=False)).any(axis=1)]
    tx_table = tx_table[['id', 'product_name', 'category', 'flow_type', 'quantity', 'amount', 'date']].copy()
    tx_table['product_name'] = tx_table.apply(lambda row: None if row['category'] in {'Sales', 'Purchases'} else row['product_name'], axis=1)
    tx_table['quantity'] = tx_table.apply(lambda row: None if row['category'] in {'Sales', 'Purchases'} else row['quantity'], axis=1)
    tx_table.columns = ['Id', 'Product', 'Category', 'Flow Type', 'Quantity', 'Amount', 'Date']
    st.dataframe(tx_table.sort_values('Date', ascending=False), use_container_width=True, hide_index=True)

    for t in txs:
        if search_term and search_term.lower() not in f"{t['product_name'] or 'No product'} {t['category']} {t['flow_type']} {t['date']}".lower():
            continue
        cols = st.columns([2, 2, 1, 1, 1, 1])
        product_label = '—' if t['category'] in {'Sales', 'Purchases'} else (t['product_name'] or 'No product')
        qty_label = '—' if t['category'] in {'Sales', 'Purchases'} else f"Qty: {t['quantity']}"
        cols[0].write(f"{t['date']} — {product_label}")
        cols[1].write(f"{t['category']} ({t['flow_type']})")
        cols[2].write(qty_label)
        cols[3].write(f"₦{t['amount']:,.2f}")
        if cols[4].button('Delete', key=f'del_tx_{t["id"]}'):
            try:
                crud.delete_transaction(t['id'])
                st.success('Transaction deleted and stock updated when needed')
                st.rerun()
            except Exception:
                st.error('Failed to delete transaction')


def main():
    init_db()
    st.set_page_config(page_title='Crucial Clothing Store', layout='wide')

    style_path = Path(__file__).resolve().parent / 'styles.css'
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

    PAGES = ['Dashboard', 'Products', 'Transactions']
    page = st.sidebar.selectbox('Navigate', PAGES)

    if page == 'Dashboard':
        dashboard()
    elif page == 'Products':
        products_page()
    elif page == 'Transactions':
        transactions_page()


if __name__ == '__main__':
    main()
