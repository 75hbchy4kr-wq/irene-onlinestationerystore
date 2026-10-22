# Irene's Online Stationery Store — Stripe Checkout (test mode first)

## Files
- `app.py`: store app with Stripe-hosted Checkout and server-side payment verification on return.
- `database.py`: SQLite tables plus safe migrations for payment fields.
- `requirements.txt`: dependencies.

## Important
- Start with Stripe **test mode**. Do not use live keys until an eligible adult account owner has completed the provider's setup and requirements.
- The app currently uses USD because product prices are displayed in dollars.
- The app reserves inventory when a pending order is created, then releases it when the customer returns through the cancel URL. Abandoned pending sessions may need manual cleanup; for a real public store, add a Stripe webhook to handle `checkout.session.completed` and `checkout.session.expired` reliably.
- Streamlit Community Cloud's local SQLite file may not be durable across restarts. For real customers, use persistent managed storage before relying on this app for live orders.

## 1. Update GitHub files
Replace `app.py` and `database.py` with these versions, and update `requirements.txt` to include `stripe>=12.0.0`.

## 2. Configure Streamlit Cloud Secrets
Open your app's **Manage app → Settings → Secrets** and add the following, replacing the placeholders:

```toml
STRIPE_SECRET_KEY = "sk_test_REPLACE_WITH_YOUR_TEST_SECRET_KEY"
APP_URL = "https://YOUR-APP-NAME.streamlit.app"

# Optional SMTP settings for order-confirmation emails
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = "587"
SMTP_USER = "your-store-sender@gmail.com"
SMTP_PASSWORD = "your-google-app-password"
SMTP_FROM = "your-store-sender@gmail.com"
```

Do not commit secrets or keys to GitHub, and never share them in chat. `APP_URL` must be the public HTTPS URL of your deployed Streamlit app, without a trailing slash. You can initially omit the SMTP settings; payment verification still works, but the app won't send the email.

## 3. Test the flow
1. Get a test secret key from the Stripe dashboard's test-mode Developers/API keys page.
2. Add it as `STRIPE_SECRET_KEY` in Streamlit Secrets.
3. Confirm product prices and inventory are correct.
4. Log in as a customer, add an item to the cart, enter an email, and click **Continue to Secure Payment**.
5. Use Stripe's official test card details in test mode only. No real charge should be made in test mode.
6. After returning to the app, it retrieves the Checkout Session from Stripe and checks `payment_status`, order ID, customer ID, session ID, amount, and currency before marking the order paid.

## Before any live launch
Ask a parent/guardian to manage the payment-provider account as required for a minor. Add a signed Stripe webhook for reliable fulfillment, replace SQLite with persistent storage, and test cancellations, failed payments, duplicate returns, and stock reservation expiry. The success-page verification is a useful project/demo implementation, but a webhook is recommended for reliable production order fulfillment.
