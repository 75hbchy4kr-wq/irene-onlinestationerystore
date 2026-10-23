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
- Pay in person has two options: (1) LT Brown International School gate, with 30-minute slots; (2) custom location request, which must be confirmed by Gmail.
- School gate hours use Taiwan time: Monday–Friday 19:00–21:00; Saturday–Sunday 08:00–20:00. Each slot is 30 minutes, and there is no per-slot customer limit.
- A school-gate order automatically sends an email with the selected date, time, and school-gate location. A custom-location order automatically sends an email acknowledging the request and clearly stating that the requested location/time are pending the store owner's reply.
- Customer order history and admin order views display the relevant shipping/pickup details.

## Pickup settings
The school pickup location and times are built into the app. No `PICKUP_LOCATION` or `PICKUP_TIME_SLOTS` secret is required for this version. Keep your existing Stripe and Gmail SMTP secrets unchanged. Only offer school pickup at a time and place allowed by the school.

## Important Stripe currency fix
Your product prices are in NT dollars and Stripe uses `twd`. TWD is a zero-decimal currency in Stripe, so this version uses whole NT dollars for `unit_amount` and for payment verification rather than multiplying by 100. Test with Stripe test mode before using real payments.

## Notes
- Shipping cost is not calculated by this demo. Make sure the customer knows any shipping fee before accepting real orders.
- The app saves addresses in its SQLite database. Streamlit Community Cloud local SQLite storage may not persist across restarts; use a persistent database before relying on it for real customers.
- For a real public store, use a Stripe webhook and persistent database for reliable fulfillment.
