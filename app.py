1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
33
34
35
36
37
38
39
40
41
42
43
44
45
46
47
48
49
50
51
52
53
54
55
56
57
58
59
60
61
62
63
64
65
66
67
68
69
70
71
72
73
74
75
76
77
78
79
80
81
82
83
84
85
86
87
88
89
90
91
92
93
94
95
96
import os
import smtplib
from email.message import EmailMessage

import bcrypt
import stripe
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
    "stripe_checkout_url": None,
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
