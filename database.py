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
    """Create the store tables. Existing data is preserved."""
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
                image_url TEXT
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

        # Safely add product_name to older order_items tables.
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(order_items)").fetchall()
        }
        if "product_name" not in columns:
            connection.execute(
                "ALTER TABLE order_items ADD COLUMN product_name TEXT NOT NULL DEFAULT ''"
            )

        # Backfill names for older order rows where possible.
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
    # Products
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            inventory INTEGER NOT NULL DEFAULT 0,
            image_url TEXT
        )
    """)

    # Orders
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            total REAL NOT NULL,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Items inside each order
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    connection.commit()
    connection.close()
