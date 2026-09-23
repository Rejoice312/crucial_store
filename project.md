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
    * id: primary key, autoincremet
    * product_id referencing products(id)
    * qaunitity int
    * amount decimal(12, 2)
    * type: must be any of ('Sales', 'Purchases')
  * expenses:
    * id: primary key, autoincrement
    * category: must be any of ('Transportation', 'Charges', )
    * amount: decimal(12, 2)

the frontend should allow the business to be able to perform crud operations through forms to
mangae its data, select boxes and other forms data validation should be used, e.g., user cant
add a sale for a product not existing or out of stock, error feedback to user should be implemented
where necessary

# business logic
* purchases and sales should update products stock_qty


# Analysis
relevant charts and tables with kpi cards shoud be included in the dashboard section.

use pages and tabs to diffrencitate sections