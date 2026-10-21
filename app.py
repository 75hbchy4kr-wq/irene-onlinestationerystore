import os
import smtplib
from email.message import EmailMessage

import bcrypt
import streamlit as st

from database import create_tables, get_connection

st.set_page_config(
    page_title="Irene's Online Stationery Store",
    page_icon="🛍️",
    layout="wide",
)

create_tables()

# -----------------------------
# SESSION STATE
# -----------------------------
DEFAULTS = {
    "logged_in": False,
    "user_id": None,
    "username": None,
    "role": None,
    "cart": {},
    "page": "Store",
}
for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


# -----------------------------
# AUTHENTICATION HELPERS
# -----------------------------
def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())


def password_matches(password: str, stored_hash) -> bool:
    try:
        if isinstance(stored_hash, str):
            stored_hash = stored_hash.encode("utf-8")
        return bcrypt.checkpw(password.encode("utf-8"), stored_hash)
    except (ValueError, TypeError):
        return False


def get_user_by_username(username):
    with get_connection() as connection:
        return connection.execute(
            "SELECT id, username, password, role FROM users WHERE username = ?",
            (username.strip(),),
        ).fetchone()



def count_admins():
    with get_connection() as connection:
        result = connection.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'admin'"
        ).fetchone()
        return result[0]



def create_user(username, password, role="customer"):
    username = username.strip()
    if len(username) < 3:
        return False, "Username must be at least 3 characters long."
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    try:
        with get_connection() as connection:
            connection.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                (username, hash_password(password).decode("utf-8"), role),
            )
        return True, "Account created successfully."
    except Exception as exc:
        if "UNIQUE" in str(exc).upper():
            return False, "That username is already taken."
        return False, "Could not create the account. Please try again."


def log_in(username, password):
    user = get_user_by_username(username)
    if user and password_matches(password, user["password"]):
        st.session_state.logged_in = True
        st.session_state.user_id = user["id"]
        st.session_state.username = user["username"]
        st.session_state.role = user["role"]
        st.session_state.page = "Store"
        st.session_state.cart = {}
        return True
    return False


def log_out():
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.cart = {}
    st.session_state.page = "Store"
    st.rerun()


# -----------------------------
# EMAIL (OPTIONAL)
# Configure SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD,
# SMTP_FROM in Streamlit secrets or environment variables.
# -----------------------------
def get_setting(name, default=""):
    try:
        return st.secrets.get(name, os.getenv(name, default))
    except Exception:
        # The app should still run when no Streamlit secrets file is configured.
        return os.getenv(name, default)


def send_order_email(to_address, username, order_id, total):
    host = get_setting("SMTP_HOST", "")
    port = int(get_setting("SMTP_PORT", "587"))
    smtp_user = get_setting("SMTP_USER", "")
    smtp_password = get_setting("SMTP_PASSWORD", "")
    from_address = get_setting("SMTP_FROM", smtp_user)

    if not (host and smtp_user and smtp_password and from_address and to_address):
        return False, "Email is not configured. The order was still saved."

    message = EmailMessage()
    message["Subject"] = f"Order confirmation #{order_id}"
    message["From"] = from_address
    message["To"] = to_address
    message.set_content(
        f"Hi {username},\n\n"
        f"Thank you for shopping at Irene's Online Stationery Store!\n"
        f"Your demo checkout order number is #{order_id}.\n"
        f"Order total: ${total:.2f}\n\n"
        "This is an order confirmation for the store's demo checkout. "
        "No real payment was processed.\n"
    )
    try:
        with smtplib.SMTP(host, port, timeout=15) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(message)
        return True, "Order confirmation email sent."
    except Exception:
        return False, "Order saved, but the email could not be sent. Check your SMTP settings."


# -----------------------------
# DATA HELPERS
# -----------------------------
def fetch_products():
    with get_connection() as connection:
        return connection.execute("""
            SELECT id, name, description, price, inventory, image_url
            FROM products
            ORDER BY name COLLATE NOCASE
        """).fetchall()


def fetch_product(product_id):
    with get_connection() as connection:
        return connection.execute("""
            SELECT id, name, description, price, inventory, image_url
            FROM products WHERE id = ?
        """, (int(product_id),)).fetchone()


def get_cart_rows():
    rows = []
    cart = st.session_state.cart
    if not cart:
        return rows
    ids = [int(product_id) for product_id in cart.keys()]
    placeholders = ",".join("?" for _ in ids)
    with get_connection() as connection:
        products = connection.execute(
            f"""SELECT id, name, price, inventory, image_url
                FROM products WHERE id IN ({placeholders})""",
            ids,
        ).fetchall()
    product_map = {row["id"]: row for row in products}
    for product_id, quantity in list(cart.items()):
        product = product_map.get(int(product_id))
        if product is None:
            continue
        rows.append({
            "id": product["id"],
            "name": product["name"],
            "price": float(product["price"]),
            "inventory": int(product["inventory"]),
            "image_url": product["image_url"],
            "quantity": int(quantity),
            "line_total": float(product["price"]) * int(quantity),
        })
    return rows


def place_order(payment_method, email_address=""):
    """Create an order and deduct stock atomically."""
    cart = st.session_state.cart
    if not cart:
        return False, "Your cart is empty.", None, 0.0

    try:
        with get_connection() as connection:
            cursor = connection.cursor()
            line_items = []
            total = 0.0

            # Validate every item before writing the order.
            for product_id, quantity in cart.items():
                quantity = int(quantity)
                if quantity < 1:
                    return False, "Invalid quantity in your cart.", None, 0.0
                product = cursor.execute(
                    "SELECT id, name, price, inventory FROM products WHERE id = ?",
                    (int(product_id),),
                ).fetchone()
                if product is None:
                    return False, "A product in your cart is no longer available.", None, 0.0
                if product["inventory"] < quantity:
                    return False, (
                        f"Not enough stock for {product['name']}. "
                        f"Only {product['inventory']} remain. Please update your cart."
                    ), None, 0.0
                price = float(product["price"])
                total += price * quantity
                line_items.append((product, quantity, price))

            status = f"Placed - {payment_method} (demo)"
            cursor.execute(
                "INSERT INTO orders (user_id, total, status) VALUES (?, ?, ?)",
                (st.session_state.user_id, round(total, 2), status),
            )
            order_id = cursor.lastrowid

            for product, quantity, price in line_items:
                # Conditional update protects stock if another checkout occurs.
                result = cursor.execute("""
                    UPDATE products
                    SET inventory = inventory - ?
                    WHERE id = ? AND inventory >= ?
                """, (quantity, product["id"], quantity))
                if result.rowcount != 1:
                    raise RuntimeError(
                        f"Stock changed while checking out {product['name']}. Please try again."
                    )
                cursor.execute("""
                    INSERT INTO order_items
                    (order_id, product_id, product_name, quantity, price)
                    VALUES (?, ?, ?, ?, ?)
                """, (order_id, product["id"], product["name"], quantity, price))

        st.session_state.cart = {}
        if email_address.strip():
            sent, email_message = send_order_email(
                email_address.strip(),
                st.session_state.username,
                order_id,
                round(total, 2),
            )
        else:
            sent, email_message = False, "No email address was entered; no email was sent."
        return True, email_message, order_id, round(total, 2)
    except Exception as exc:
        return False, str(exc), None, 0.0


# -----------------------------
# CUSTOMER STORE
# -----------------------------
def customer_store():
    st.title("🛍️ Irene's Online Stationery Store")
    st.write("Find something lovely for your desk, notes, and next big idea.")

    products = fetch_products()
    if not products:
        st.info("There are currently no products in the store.")
        return

    for product in products:
        with st.container(border=True):
            col1, col2 = st.columns([1, 2])
            with col1:
                if product["image_url"]:
                    try:
                        st.image(product["image_url"], use_container_width=True)
                    except Exception:
                        st.caption("Product image could not be loaded.")
            with col2:
                st.subheader(product["name"])
                st.write(product["description"] or "No description yet.")
                st.write(f"💰 **${float(product['price']):.2f}**")
                stock = int(product["inventory"])
                if stock <= 0:
                    st.error("Out of stock")
                else:
                    st.write(f"📦 {stock} available")
                    if stock <= 5:
                        st.caption("Only a few left!")
                    cart_qty = int(st.session_state.cart.get(product["id"], 0))
                    if cart_qty:
                        st.caption(f"In your cart: {cart_qty}")
                    if st.button("🛒 Add to Cart", key=f"add_{product['id']}"):
                        if cart_qty >= stock:
                            st.warning("Your cart already contains the available stock limit.")
                        else:
                            st.session_state.cart[product["id"]] = cart_qty + 1
                            st.toast(f"{product['name']} added to your cart!")
                        st.rerun()


# -----------------------------
# CART
# -----------------------------
def cart_page():
    st.title("🛒 Your Shopping Cart")
    rows = get_cart_rows()
    if not rows:
        st.info("Your cart is empty. Add a product from the store to get started.")
        if st.button("Browse Store"):
            st.session_state.page = "Store"
            st.rerun()
        return

    total = 0.0
    for row in rows:
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
            with col1:
                st.write(f"**{row['name']}**")
                st.write(f"${row['price']:.2f} each")
            with col2:
                new_quantity = st.number_input(
                    "Quantity",
                    min_value=1,
                    max_value=max(1, row["inventory"]),
                    value=min(row["quantity"], max(1, row["inventory"])),
                    step=1,
                    key=f"cart_qty_{row['id']}",
                )
                if new_quantity != row["quantity"]:
                    st.session_state.cart[row["id"]] = int(new_quantity)
                    st.rerun()
            with col3:
                line_total = row["price"] * row["quantity"]
                st.write(f"**${line_total:.2f}**")
            with col4:
                if st.button("Remove", key=f"remove_{row['id']}"):
                    st.session_state.cart.pop(row["id"], None)
                    st.rerun()
            if row["quantity"] > row["inventory"]:
                st.warning(
                    f"Only {row['inventory']} currently in stock. "
                    "Please reduce this quantity."
                )
        total += row["price"] * row["quantity"]

    st.divider()
    st.subheader(f"Subtotal: ${total:.2f}")
    st.caption("Shipping and taxes are not calculated in this demo store.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Continue Shopping"):
            st.session_state.page = "Store"
            st.rerun()
    with col2:
        if st.button("Proceed to Checkout", type="primary"):
            st.session_state.page = "Checkout"
            st.rerun()


# -----------------------------
# CHECKOUT
# -----------------------------
def checkout_page():
    st.title("💳 Checkout")
    rows = get_cart_rows()
    if not rows:
        st.info("Your cart is empty.")
        if st.button("Return to Store"):
            st.session_state.page = "Store"
            st.rerun()
        return

    total = sum(row["line_total"] for row in rows)
    st.subheader("Order summary")
    for row in rows:
        st.write(
            f"- {row['name']} × {row['quantity']} — ${row['line_total']:.2f}"
        )
    st.markdown(f"### Total: ${total:.2f}")
    st.warning(
        "Demo payment only: no real payment is taken and no card details should be entered."
    )
    payment_method = st.radio(
        "Choose a demo payment method",
        ["Demo checkout (no payment)", "Pay on collection (demo)"],
    )
    email_address = st.text_input(
        "Email for order confirmation (optional)",
        placeholder="you@example.com",
    )
    if st.button("Place Order", type="primary"):
        ok, message, order_id, final_total = place_order(payment_method, email_address)
        if ok:
            st.session_state.last_order = {
                "id": order_id,
                "total": final_total,
                "message": message,
            }
            st.session_state.page = "Order Confirmation"
            st.rerun()
        else:
            st.error(message)

    if st.button("← Back to Cart"):
        st.session_state.page = "Cart"
        st.rerun()


def order_confirmation_page():
    order = st.session_state.get("last_order")
    st.title("✅ Order Confirmation")
    if not order:
        st.info("No recent order confirmation is available in this session.")
    else:
        st.success(f"Your order #{order['id']} was saved successfully!")
        st.write(f"**Order total:** ${order['total']:.2f}")
        st.caption(order["message"])
        st.write("This was a demo checkout; no real payment was processed.")
    if st.button("Continue Shopping", type="primary"):
        st.session_state.page = "Store"
        st.rerun()


# -----------------------------
# ORDER HISTORY
# -----------------------------
def order_history_page():
    st.title("📜 My Order History")
    with get_connection() as connection:
        orders = connection.execute("""
            SELECT id, total, status, created_at
            FROM orders
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
        """, (st.session_state.user_id,)).fetchall()

        order_items = {}
        for order in orders:
            order_items[order["id"]] = connection.execute("""
                SELECT product_name, quantity, price
                FROM order_items
                WHERE order_id = ?
                ORDER BY id
            """, (order["id"],)).fetchall()

    if not orders:
        st.info("You have not placed any orders yet.")
        return

    for order in orders:
        with st.expander(
            f"Order #{order['id']} · ${float(order['total']):.2f} · {order['created_at']}"
        ):
            st.write(f"**Status:** {order['status']}")
            for item in order_items[order["id"]]:
                st.write(
                    f"- {item['product_name']} × {item['quantity']} "
                    f"at ${float(item['price']):.2f} each"
                )
            st.write(f"**Total: ${float(order['total']):.2f}**")


# -----------------------------
# ADMIN PRODUCT MANAGEMENT
# -----------------------------
def admin_add_product():
    st.subheader("➕ Add Product")
    with st.form("add_product_form", clear_on_submit=True):
        name = st.text_input("Product name")
        description = st.text_area("Description")
        price = st.number_input("Price ($)", min_value=0.0, value=1.0, step=0.5)
        inventory = st.number_input("Starting inventory", min_value=0, value=0, step=1)
        image_url = st.text_input("Image URL (optional)")
        submitted = st.form_submit_button("Add Product")
    if submitted:
        if not name.strip():
            st.error("Please enter a product name.")
        else:
            with get_connection() as connection:
                connection.execute("""
                    INSERT INTO products (name, description, price, inventory, image_url)
                    VALUES (?, ?, ?, ?, ?)
                """, (name.strip(), description.strip(), float(price), int(inventory),
                      image_url.strip() or None))
            st.success(f"{name.strip()} added successfully.")
            st.rerun()


def admin_edit_products():
    st.subheader("✏️ Edit Products")
    products = fetch_products()
    if not products:
        st.info("No products to edit yet.")
        return
    options = {f"{p['name']} (ID {p['id']})": p["id"] for p in products}
    selected_label = st.selectbox("Choose a product", list(options.keys()))
    product = fetch_product(options[selected_label])
    if not product:
        st.error("That product could not be found.")
        return
    with st.form(f"edit_product_{product['id']}"):
        name = st.text_input("Product name", value=product["name"])
        description = st.text_area("Description", value=product["description"] or "")
        price = st.number_input(
            "Price ($)", min_value=0.0, value=float(product["price"]), step=0.5
        )
        inventory = st.number_input(
            "Inventory", min_value=0, value=int(product["inventory"]), step=1
        )
        image_url = st.text_input("Image URL", value=product["image_url"] or "")
        submitted = st.form_submit_button("Save Changes")
    if submitted:
        if not name.strip():
            st.error("Product name cannot be empty.")
        else:
            with get_connection() as connection:
                connection.execute("""
                    UPDATE products
                    SET name = ?, description = ?, price = ?, inventory = ?, image_url = ?
                    WHERE id = ?
                """, (name.strip(), description.strip(), float(price), int(inventory),
                      image_url.strip() or None, product["id"]))
            st.success("Product updated.")
            st.rerun()


def admin_manage_inventory():
    st.subheader("📦 Manage Inventory")
    products = fetch_products()
    if not products:
        st.info("No products are available.")
        return
    for product in products:
        col1, col2, col3 = st.columns([3, 2, 2])
        with col1:
            st.write(f"**{product['name']}** (ID {product['id']})")
        with col2:
            st.write(f"${float(product['price']):.2f}")
        with col3:
            stock = int(product["inventory"])
            if stock == 0:
                st.error("Out of stock")
            elif stock <= 5:
                st.warning(f"Low stock: {stock}")
            else:
                st.write(f"In stock: {stock}")
        with st.form(f"inventory_{product['id']}"):
            new_stock = st.number_input(
                "Set stock quantity",
                min_value=0,
                value=int(product["inventory"]),
                step=1,
                key=f"inventory_input_{product['id']}",
            )
            if st.form_submit_button("Save Stock"):
                with get_connection() as connection:
                    connection.execute(
                        "UPDATE products SET inventory = ? WHERE id = ?",
                        (int(new_stock), product["id"]),
                    )
                st.success(f"Stock updated for {product['name']}.")
                st.rerun()
        st.divider()


def admin_delete_products():
    st.subheader("🗑️ Delete Products")
    products = fetch_products()
    if not products:
        st.info("No products to delete.")
        return
    options = {f"{p['name']} (ID {p['id']})": p["id"] for p in products}
    selected_label = st.selectbox("Choose a product to delete", list(options.keys()))
    st.warning("Deleting a product cannot be undone. Past orders keep a snapshot of its name.")
    confirm = st.checkbox("I understand and want to delete this product.")
    if st.button("Delete Selected Product", type="primary", disabled=not confirm):
        product_id = options[selected_label]
        try:
            with get_connection() as connection:
                connection.execute("DELETE FROM products WHERE id = ?", (product_id,))
            st.session_state.cart.pop(product_id, None)
            st.success("Product deleted.")
            st.rerun()
        except Exception:
            st.error(
                "This product may be referenced by an existing order. "
                "To preserve order history, it cannot be deleted from this database."
            )


def admin_orders():
    st.subheader("🧾 All Orders")
    with get_connection() as connection:
        orders = connection.execute("""
            SELECT orders.id, users.username, orders.total, orders.status, orders.created_at
            FROM orders
            JOIN users ON users.id = orders.user_id
            ORDER BY orders.created_at DESC, orders.id DESC
        """).fetchall()
    if not orders:
        st.info("No orders have been placed yet.")
        return
    for order in orders:
        with st.expander(
            f"Order #{order['id']} · {order['username']} · ${float(order['total']):.2f}"
        ):
            st.write(f"**Date:** {order['created_at']}")
            st.write(f"**Status:** {order['status']}")
            with get_connection() as connection:
                items = connection.execute("""
                    SELECT product_name, quantity, price
                    FROM order_items WHERE order_id = ? ORDER BY id
                """, (order["id"],)).fetchall()
            for item in items:
                st.write(
                    f"- {item['product_name']} × {item['quantity']} "
                    f"— ${float(item['price']) * int(item['quantity']):.2f}"
                )


# -----------------------------
# LOGIN / SIGNUP / FIRST ADMIN SETUP
# -----------------------------
def auth_screen():
    st.title("🛍️ Irene's Online Stationery Store")
    st.write("Welcome! Sign in to continue or create a customer account.")

    if count_admins() == 0:
        st.warning(
            "First-time setup: create the store's administrator account. "
            "Once created, this setup panel will disappear."
        )
        with st.form("first_admin_form"):
            admin_username = st.text_input("Admin username")
            admin_password = st.text_input("Admin password", type="password")
            admin_password_again = st.text_input("Confirm admin password", type="password")
            create_admin = st.form_submit_button("Create Admin Account")
        if create_admin:
            if admin_password != admin_password_again:
                st.error("The passwords do not match.")
            else:
                ok, message = create_user(admin_username, admin_password, "admin")
                if ok:
                    st.success("Admin account created. Please log in below.")
                    st.rerun()
                else:
                    st.error(message)

    login_tab, signup_tab = st.tabs(["Log In", "Customer Sign Up"])
    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Log In", type="primary")
        if submitted:
            if log_in(username, password):
                st.rerun()
            else:
                st.error("Incorrect username or password.")

    with signup_tab:
        with st.form("signup_form", clear_on_submit=True):
            new_username = st.text_input("Choose a username", key="signup_username")
            new_password = st.text_input("Choose a password (8+ characters)", type="password")
            confirm_password = st.text_input("Confirm password", type="password")
            signup = st.form_submit_button("Create Customer Account")
        if signup:
            if new_password != confirm_password:
                st.error("The passwords do not match.")
            else:
                ok, message = create_user(new_username, new_password, "customer")
                if ok:
                    st.success("Account created! You can now log in.")
                else:
                    st.error(message)


# -----------------------------
# MAIN APP
# -----------------------------
if not st.session_state.logged_in:
    auth_screen()
    st.stop()

# Refresh the user record so deleted accounts or changed roles don't linger in session.
with get_connection() as connection:
    current_user = connection.execute(
        "SELECT id, username, role FROM users WHERE id = ?",
        (st.session_state.user_id,),
    ).fetchone()
if not current_user:
    log_out()

st.sidebar.title("🛍️ Irene's Store")
st.sidebar.write(f"Signed in as **{st.session_state.username}**")
st.sidebar.caption(f"Role: {st.session_state.role.title()}")

if st.session_state.role == "admin":
    page_options = [
        "Store Preview", "Add Product", "Edit Products",
        "Manage Inventory", "Delete Products", "All Orders"
    ]
else:
    page_options = ["Store", "Cart", "Order History"]

def sync_navigation():
    st.session_state.page = st.session_state.nav_radio


# Keep the navigation radio separate from checkout/confirmation pages so
# those pages do not get overwritten by the sidebar on reruns.
if "nav_radio" not in st.session_state or st.session_state.nav_radio not in page_options:
    st.session_state.nav_radio = (
        st.session_state.page if st.session_state.page in page_options else page_options[0]
    )

st.sidebar.radio(
    "Navigation",
    page_options,
    key="nav_radio",
    on_change=sync_navigation,
)

# Route based on the current page, including pages that are not sidebar options.
current_page = st.session_state.page

if st.session_state.role == "admin":
    if current_page == "Add Product":
        admin_add_product()
    elif current_page == "Edit Products":
        admin_edit_products()
    elif current_page == "Manage Inventory":
        admin_manage_inventory()
    elif current_page == "Delete Products":
        admin_delete_products()
    elif current_page == "All Orders":
        admin_orders()
    else:
        customer_store()
else:
    if current_page == "Checkout":
        checkout_page()
    elif current_page == "Order Confirmation":
        order_confirmation_page()
    elif current_page == "Cart":
        cart_page()
    elif current_page == "Order History":
        order_history_page()
    else:
        customer_store()

# Cart is available in the sidebar for customers.
if st.session_state.role == "customer":
    st.sidebar.metric("Cart items", sum(st.session_state.cart.values()))
    if st.sidebar.button("Go to Cart"):
        st.session_state.page = "Cart"
        st.session_state.nav_radio = "Cart"
        st.rerun()

if st.sidebar.button("Log Out"):
    log_out()
