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

    col1, col2, col3 = st.columns(3)

    with col1:
        st.button("➕ Add Product")

    with col2:
        st.button("✏️ Edit Products")

    with col3:
        st.button("📦 Manage Inventory")

    st.divider()

    if st.button("Log Out"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.role = None
        st.rerun()


# -----------------------------
# MAIN APP
# -----------------------------

if not st.session_state.logged_in:

    login_page()

elif st.session_state.role == "admin":

    admin_dashboard()
