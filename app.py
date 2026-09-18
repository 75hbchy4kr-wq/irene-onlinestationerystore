import streamlit as st
import bcrypt

from database import create_tables


# -----------------------------
# DATABASE
# -----------------------------

create_tables()


# -----------------------------
# PAGE SETTINGS
# -----------------------------

st.set_page_config(
    page_title="Irene's Online Stationery Store",
    page_icon="🛍️",
    layout="wide"
)


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

    st.title("🛍️ Irene's Online Stationery Store")

    st.subheader("Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        # Admin login
        admin_username = st.secrets["admin"]["username"]
        admin_password = st.secrets["admin"]["password"]

        if username == admin_username and password == admin_password:

            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.role = "admin"

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
            "📦 Manage Inventory"
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

        st.info(
            "Product editing will be added next."
        )

    # -----------------------------
    # INVENTORY
    # -----------------------------

    elif option == "📦 Manage Inventory":

        st.header("📦 Manage Inventory")

        st.info(
            "Inventory management will be added next."
        )

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
