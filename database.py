from pathlib import Path
import sqlite3

DATABASE = Path(__file__).resolve().parent / "store.db"


def get_connection():
    connection = sqlite3.connect(str(DATABASE), timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 15000")
    return connection


def create_tables():
    """Create store tables and safely migrate existing orders without deleting data."""
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('admin', 'customer'))
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL CHECK (price >= 0),
                inventory INTEGER NOT NULL DEFAULT 0 CHECK (inventory >= 0),
                image_url TEXT,
                category TEXT NOT NULL DEFAULT 'Items'
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                total REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'Placed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER,
                product_name TEXT NOT NULL DEFAULT '',
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
            )
        """)

        product_columns = {row["name"] for row in connection.execute("PRAGMA table_info(products)")}
        if "category" not in product_columns:
            connection.execute("ALTER TABLE products ADD COLUMN category TEXT NOT NULL DEFAULT 'Items'")

        order_columns = {row["name"] for row in connection.execute("PRAGMA table_info(orders)")}
        migrations = {
            "customer_email": "ALTER TABLE orders ADD COLUMN customer_email TEXT NOT NULL DEFAULT ''",
            "stripe_session_id": "ALTER TABLE orders ADD COLUMN stripe_session_id TEXT",
            "email_sent": "ALTER TABLE orders ADD COLUMN email_sent INTEGER NOT NULL DEFAULT 0",
            "pickup_date": "ALTER TABLE orders ADD COLUMN pickup_date TEXT",
            "pickup_time": "ALTER TABLE orders ADD COLUMN pickup_time TEXT",
            "pickup_location": "ALTER TABLE orders ADD COLUMN pickup_location TEXT",
            "fulfillment_method": "ALTER TABLE orders ADD COLUMN fulfillment_method TEXT NOT NULL DEFAULT 'pickup'",
            "customer_name": "ALTER TABLE orders ADD COLUMN customer_name TEXT NOT NULL DEFAULT ''",
            "customer_phone": "ALTER TABLE orders ADD COLUMN customer_phone TEXT NOT NULL DEFAULT ''",
            "shipping_region": "ALTER TABLE orders ADD COLUMN shipping_region TEXT",
            "shipping_city": "ALTER TABLE orders ADD COLUMN shipping_city TEXT",
            "shipping_postal_code": "ALTER TABLE orders ADD COLUMN shipping_postal_code TEXT",
            "shipping_address_line1": "ALTER TABLE orders ADD COLUMN shipping_address_line1 TEXT",
            "shipping_address_line2": "ALTER TABLE orders ADD COLUMN shipping_address_line2 TEXT",
        }
        for column, sql in migrations.items():
            if column not in order_columns:
                connection.execute(sql)

        item_columns = {row["name"] for row in connection.execute("PRAGMA table_info(order_items)")}
        if "product_name" not in item_columns:
            connection.execute("ALTER TABLE order_items ADD COLUMN product_name TEXT NOT NULL DEFAULT ''")
        connection.execute("""
            UPDATE order_items
            SET product_name = COALESCE(
                (SELECT name FROM products WHERE products.id = order_items.product_id),
                'Deleted product'
            )
            WHERE product_name = ''
        """)


def check_database():
    with get_connection() as connection:
        row = connection.execute("SELECT COUNT(*) AS count FROM products").fetchone()
        return row["count"]
