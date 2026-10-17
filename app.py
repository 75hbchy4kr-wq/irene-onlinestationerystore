import streamlit as st
import bcrypt

from database import create_tables, check_database, get_connection

st.set_page_config(
    page_title="Irene's Online Stationery Store",
    page_icon="🛍️",
    layout="wide"
)

create_tables()

st.write("Products currently in database:", check_database())


# -----------------------------
# SESSION STATE
# -----------------------------

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = None

if "role" not in st.session_state:
    st.session_state.role = None


# -----------------------------
# LOGIN PAGE
# -----------------------------


def login_page():

    from database import get_connection

    st.title("🛍️ Irene's Online Stationery Store")

    page = st.radio(
        "Account",
        ["Login", "Sign Up"],
        horizontal=True
    )

    # CUSTOMER SIGN UP
    if page == "Sign Up":
        st.subheader("Create a Customer Account")

        username = st.text_input(
            "Choose a Username",
            key="signup_username"
        )

        password = st.text_input(
            "Choose a Password",
            type="password",
            key="signup_password"
        )

        confirm_password = st.text_input(
            "Confirm Password",
            type="password"
        )

        if st.button("Create Account"):

            username = username.strip()

            if not username or not password:
                st.error("Please complete all fields.")

            elif len(password) < 8:
                st.error("Password must be at least 8 characters.")

            elif password != confirm_password:
                st.error("Passwords do not match.")

            else:
                connection = get_connection()
                cursor = connection.cursor()

                cursor.execute(
                    "SELECT id FROM users WHERE username = ?",
                    (username,)
                )

                existing_user = cursor.fetchone()

                if existing_user:
                    st.error("Username already exists.")

                else:
                    hashed_password = bcrypt.hashpw(
                        password.encode("utf-8"),
                        bcrypt.gensalt()
                    ).decode("utf-8")

                    cursor.execute(
                        """
                        INSERT INTO users (username, password, role)
                        VALUES (?, ?, ?)
                        """,
                        (username, hashed_password, "customer")
                    )

                    connection.commit()
                    st.success(
                        "Account created! Select Login to sign in."
                    )

                connection.close()

    # LOGIN
    else:
        st.subheader("Login")

        username = st.text_input("Username")
        password = st.text_input(
            "Password",
            type="password"
        )

        if st.button("Login"):

            # ADMIN LOGIN
            admin_username = st.secrets["admin"]["username"]
            admin_password = st.secrets["admin"]["password"]

            if (
                username == admin_username
                and password == admin_password
            ):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.role = "admin"
                st.rerun()

            # CUSTOMER LOGIN
            else:
                connection = get_connection()
                cursor = connection.cursor()

                cursor.execute(
                    """
                    SELECT password, role
                    FROM users
                    WHERE username = ?
                    """,
                    (username.strip(),)
                )

                user = cursor.fetchone()
                connection.close()

                if (
                    user
                    and user[1] == "customer"
                    and bcrypt.checkpw(
                        password.encode("utf-8"),
                        user[0].encode("utf-8")
                    )
                ):
                    st.session_state.logged_in = True
                    st.session_state.username = username.strip()
                    st.session_state.role = "customer"
                    st.rerun()

                else:
                    st.error("Incorrect username or password.")


# -----------------------------
# ADMIN DASHBOARD
# -----------------------------


def admin_dashboard():

    st.title("👑 Admin Dashboard")

    st.write(f"Welcome, **{st.session_state.username}**!")

    st.divider()
    
    st.subheader("Store Management")

    option = st.selectbox(
        "Choose an action",
        [
            "Select an action...",
            "➕ Add Product",
            "✏️ Edit Products",
            "📦 Manage Inventory",
            "🗑️ Delete Products",
            "🛒 View Store"
        ]
    )

    # -----------------------------
    # ADD PRODUCT
    # -----------------------------

    if option == "➕ Add Product":

        st.header("➕ Add a New Product")

        product_name = st.text_input("Product Name")

        description = st.text_area("Product Description")

        price = st.number_input(
            "Price",
            min_value=0.0,
            step=0.01
        )

        inventory = st.number_input(
            "Inventory / Stock",
            min_value=0,
            step=1
        )

        image_url = st.text_input(
            "Product Image URL"
        )

        if st.button("Add Product to Store"):

            if product_name.strip() == "":
                st.error("Please enter a product name.")

            else:

                from database import get_connection

                connection = get_connection()
                cursor = connection.cursor()

                cursor.execute(
                    """
                    INSERT INTO products
                    (name, description, price, inventory, image_url)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        product_name,
                        description,
                        price,
                        inventory,
                        image_url
                    )
                )

                connection.commit()
                connection.close()

                st.success(
                    f"✅ {product_name} was added to your store!"
                )

    # -----------------------------
    # EDIT PRODUCTS
    # -----------------------------

   
    elif option == "✏️ Edit Products":

        st.header("✏️ Edit Products")

        from database import get_connection

        connection = get_connection()
        products = connection.execute(
            """
            SELECT id, name, description, price, inventory, image_url
            FROM products
            ORDER BY name
            """
        ).fetchall()
        connection.close()

        if not products:
            st.info("There are no products to edit.")

        else:
            product_options = {
                f"{product[1]} (ID: {product[0]})": product[0]
                for product in products
            }

            selected = st.selectbox(
                "Choose a product",
                list(product_options.keys()),
                key="edit_product_select"
            )

            product_id = product_options[selected]

            product = next(
                p for p in products if p[0] == product_id
            )

            with st.form("edit_product_form"):

                name = st.text_input(
                    "Product Name",
                    value=product[1]
                )

                description = st.text_area(
                    "Description",
                    value=product[2] or ""
                )

                price = st.number_input(
                    "Price",
                    min_value=0.01,
                    value=max(float(product[3]), 0.01),
                    step=0.01
                )

                inventory = st.number_input(
                    "Stock Quantity",
                    min_value=0,
                    value=max(int(product[4]), 0),
                    step=1
                )

                image_url = st.text_input(
                    "Product Image URL",
                    value=product[5] or ""
                )

                submitted = st.form_submit_button(
                    "Save Changes"
                )

            if submitted:

                if not name.strip():
                    st.error("Product name cannot be empty.")

                else:
                    connection = get_connection()

                    try:
                        connection.execute(
                            """
                            UPDATE products
                            SET name = ?,
                                description = ?,
                                price = ?,
                                inventory = ?,
                                image_url = ?
                            WHERE id = ?
                            """,
                            (
                                name.strip(),
                                description,
                                price,
                                inventory,
                                image_url.strip(),
                                product_id
                            )
                        )
                        connection.commit()

                    finally:
                        connection.close()

                    st.success("Product updated successfully!")
                    st.rerun()


    # -----------------------------
    # INVENTORY
    # -----------------------------

  
    elif option == "📦 Manage Inventory":
        st.header("📦 Manage Inventory")

        from database import get_connection

        connection = get_connection()
        try:
            products = connection.execute(
                "SELECT id, name, price, inventory FROM products ORDER BY name"
            ).fetchall()
        finally:
            connection.close()

        if not products:
            st.info("There are no products in your store yet.")
        else:
            st.subheader("Current Stock")

            for product_id, name, price, inventory in products:
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])

                    with col1:
                        st.write(f"**{name}**")
                        st.caption(f"Price: ${price:.2f}")

                        if inventory == 0:
                            st.error("Out of stock")
                        elif inventory <= 5:
                            st.warning(f"Low stock: {inventory} left")
                        else:
                            st.write(f"Stock: {inventory} units")

                    with col2:
                        with st.form(f"stock_form_{product_id}"):
                            new_stock = st.number_input(
                                "Update stock",
                                min_value=0,
                                value=max(int(inventory), 0),
                                step=1,
                                key=f"stock_input_{product_id}"
                            )

                            save_stock = st.form_submit_button("Save Stock")

                        if save_stock:
                            connection = get_connection()
                            try:
                                connection.execute(
                                    "UPDATE products SET inventory = ? WHERE id = ?",
                                    (int(new_stock), product_id)
                                )
                                connection.commit()
                            finally:
                                connection.close()

                            st.success(f"Updated stock for {name}!")
                            st.rerun()

    # -----------------------------
    # DELETE PRODUCTS
    # -----------------------------

    elif option == "🗑️ Delete Products":

        st.header("🗑️ Delete Products")

        from database import get_connection

        connection = get_connection()

        try:
            products = connection.execute(
                "SELECT id, name FROM products ORDER BY name"
            ).fetchall()
        finally:
            connection.close()

        if not products:
            st.info("There are no products to delete.")

        else:
            product_options = {
                f"{name} (ID: {product_id})": product_id
                for product_id, name in products
            }

            selected_product = st.selectbox(
                "Choose a product to delete",
                list(product_options.keys()),
                key="delete_product_select"
            )

            confirm = st.checkbox(
                "I confirm I want to delete this product.",
                key="confirm_delete_product"
            )

            if st.button("Delete Product", type="primary"):

                if not confirm:
                    st.warning("Please confirm before deleting.")

                else:
                    product_id = product_options[selected_product]

                    connection = get_connection()

                    try:
                        connection.execute(
                            "DELETE FROM products WHERE id = ?",
                            (product_id,)
                        )
                        connection.commit()
                    finally:
                        connection.close()

                    st.success("Product deleted successfully!")
                    st.rerun()

    st.divider()

    if st.button("Log Out"):

        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.role = None

        st.rerun()
# -----------------------------
# CUSTOMER STORE
# -----------------------------

def customer_store():

    st.title("🛍️ Irene's Online Stationery Store")

    st.write("Welcome to the store!")

    from database import get_connection

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, name, description, price, inventory, image_url
        FROM products
    """)

    products = cursor.fetchall()

    connection.close()

    if not products:
        st.info("There are currently no products in the store.")

    else:

        st.subheader("✨ Our Products")

        for product in products:

            product_id = product[0]
            name = product[1]
            description = product[2]
            price = product[3]
            inventory = product[4]
            image_url = product[5]

            with st.container():

                col1, col2 = st.columns([1, 2])

                with col1:

                    if image_url:
                        st.image(
                            image_url,
                            use_container_width=True
                        )

                with col2:

                    st.subheader(name)

                    st.write(description)

                    st.write(f"💰 **${price:.2f}**")

                    if inventory > 0:
                        st.write(
                            f"📦 {inventory} available"
                        )

                        st.button(
                            "🛒 Add to Cart",
                            key=f"add_{product_id}"
                        )

                    else:
                        st.error("Out of stock")

                st.divider()# -----------------------------
# MAIN APP
# -----------------------------

if not st.session_state.logged_in:

    login_page()

elif st.session_state.role == "admin":

    admin_dashboard()

elif st.session_state.role == "customer":

    customer_store()
