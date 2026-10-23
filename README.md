# Irene's Online Store — Shipping Address + Pickup Time Update

This update is based on your current app.py/database.py and keeps the existing chatbot.py file.

## Files to replace
- Replace `app.py` with the included file.
- Replace `database.py` with the included file.
- Replace `requirements.txt` with the included file.
- **Do not delete or replace `chatbot.py`**; the app imports it.
- Do not delete `store.db`. The new `database.py` adds the new columns automatically on startup.

## New checkout behavior
- Online payment + shipping: customer enters recipient name, phone, county/city, district/township, postal code (optional), street address, and optional floor/room notes. These are saved to the order and shown to the admin.
- Pay in person at pickup: customer enters name and phone, chooses a date and a time slot. Pickup location is set by the store owner in Streamlit Secrets.
- Customer order history and order confirmation display the relevant shipping/pickup details.
- Pickup confirmation email includes date, time, and location.

## Configure pickup location/time slots
In Streamlit Community Cloud: Manage app → Settings → Secrets. Add or adjust:

```toml
PICKUP_LOCATION = "A school-approved public meeting area; confirm the exact point by email"
PICKUP_TIME_SLOTS = "12:00–12:15,12:15–12:30,12:30–12:45,15:30–15:45,15:45–16:00,16:00–16:15,16:15–16:30"
```

Choose times and locations that are actually allowed by your school. The defaults are examples; change them to match your schedule. If your Streamlit Secrets already has Stripe and Gmail SMTP settings, keep those existing entries and add these two settings underneath them.

## Important Stripe currency fix
Your product prices are in NT dollars and Stripe uses `twd`. TWD is a zero-decimal currency in Stripe, so this version uses whole NT dollars for `unit_amount` and for payment verification rather than multiplying by 100. Test with Stripe test mode before using real payments.

## Notes
- Shipping cost is not calculated by this demo. Make sure the customer knows any shipping fee before accepting real orders.
- The app saves addresses in its SQLite database. Streamlit Community Cloud local SQLite storage may not persist across restarts; use a persistent database before relying on it for real customers.
- For a real public store, use a Stripe webhook and persistent database for reliable fulfillment.
