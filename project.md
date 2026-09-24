rewrite this whole project, preserving just this file as it is.

the aim is to create a business management platform for a business with the details below:

busineness name: Crucial Clothing Store


the app should have:
* a streamlit frontend in one folder styled beautifully with css, 
* a backend of all relevant functions in a different folder
* a sqlite database for storage. the tables are as follows:
  * products:
    * id: primary key, autoincrement
    * name: varchar(20) not null
    * description: varchar(200) can be null
    * stock_qty: int
  * transactions:
    * id: primary key, autoincrement
    * product_id: references products(id), nullable for non-inventory items
    * category: must be one of ('Sales', 'Purchases', 'Wages', 'Loan Repayment', 'Lending', 'Other Expenses', 'Capital', 'Other Income', 'Transportation', 'Maintenance')
    * flow_type: must be 'Inflow' or 'Outflow', automatically derived by category
    * quantity: int, default 0
    * amount: decimal(12, 2)
    * description: text
    * date: default current date

# business logic
* sales and purchases update products stock_qty when tied to inventory
* flow type is determined internally from the transaction category and is not selected by the user

# Analysis
relevant charts and tables with kpi cards should be included in the dashboard section.

use pages and tabs to diffrencitate sections