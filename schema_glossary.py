GLOSSARY = {

    # Revenue / Sales
    "revenue": "price",
    "sales": "price",
    "total revenue": "SUM(price)",
    "total sales": "SUM(price)",

    # Orders
    "orders": "order_id",
    "total orders": "COUNT(order_id)",
    "number of orders": "COUNT(order_id)",

    # Customers
    "customers": "customer_id",
    "unique customers": "COUNT(DISTINCT customer_id)",

    # Location
    "state": "customer_state",
    "region": "customer_state",
    "city": "customer_city",

    # Products
    "product": "product_id",
    "category": "product_category_name",

    # Time
    "date": "order_purchase_timestamp",
    "month": "strftime('%Y-%m', order_purchase_timestamp)",
    "year": "strftime('%Y', order_purchase_timestamp)",

    # Reviews
    "rating": "review_score",

    # Payments
    "payment": "payment_value",
    "payment method": "payment_type",

    # Sorting / Ranking
    "top": "ORDER BY DESC LIMIT",
    "highest": "ORDER BY DESC",
    "lowest": "ORDER BY ASC"
}