# irene-onlinestationerystore
# Irene's Online Stationery Store — Complete Version

## Files
- `app.py`: Streamlit app (accounts, admin, storefront, cart, checkout demo, order history, optional email).
- `database.py`: SQLite database setup and helpers.
- `requirements.txt`: Python dependencies.

## Run locally
1. Put `app.py`, `database.py`, and `requirements.txt` in the same project folder.
2. Keep your existing `store.db` in that folder if you want to preserve existing users/products/orders.
3. Install dependencies: `pip install -r requirements.txt`
4. Start the app: `streamlit run app.py`

## First admin account
If the database has no admin account, the app shows a first-time setup form to create one.
Use a strong password of at least 8 characters. After the first admin exists, the setup form disappears.

## Existing database
Make a backup of `store.db` before replacing files. The database setup adds `product_name` to older `order_items` tables when needed and preserves existing rows.
If your existing `users` or `products` tables have a different schema, restore the backup and ask for help adapting the migration before running this version.

## Demo checkout
The checkout is not connected to a payment processor. It does not collect card numbers or take real payments. Orders are saved and stock is deducted only when checkout succeeds.

## Optional email confirmations
Set these in Streamlit secrets (recommended) or environment variables:
- `SMTP_HOST`
- `SMTP_PORT` (usually `587`)
- `SMTP_USER`
- `SMTP_PASSWORD`
- `SMTP_FROM`

The customer can enter an email address at checkout. Email is optional; an order is still saved if email is not configured or fails.

For Streamlit Cloud, add settings under the app's **Settings → Secrets**, for example:

```toml
SMTP_HOST = "smtp.example.com"
SMTP_PORT = 587
SMTP_USER = "your-smtp-user"
SMTP_PASSWORD = "your-smtp-password"
SMTP_FROM = "orders@example.com"
```

Do not put real passwords in code or commit secrets to a public repository.
