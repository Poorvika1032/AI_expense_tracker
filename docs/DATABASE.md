# Database

SQLite is stored at `database.db` beside `app.py`. Initialization is additive and enables foreign keys.

- `users`: identity, password hash, role/status, profile preferences, theme, and generated profile-image filename.
- `travel_history`: compatible legacy prediction rows with optional start/end dates.
- `expenses`: actual expense entries linked to a trip and user.
- `wishlist`: saved user destinations, optional estimates, dates, and notes.
- `favorite_destinations`: user-scoped favorites.
- `user_savings`: model-based optimizer scenarios, including potential savings and (for linked trips) actual expense totals and signed predicted-minus-actual variance.
- `notifications`: budget/upcoming-trip notices with read state.
- `exchange_rates`: cached daily currency reference rates.
- `datasets`: metadata for CSV uploads stored under generated names in `dataset/uploads/`.
- `model_versions`: model artifact paths, training metrics, and active-version state.
- `activity_logs`: login, registration, prediction, dataset, model training, and admin status events.

Indexes cover trips, expenses, and wishlist access. Monetary values use INR in application calculations. The profile currency code is a preference only and does not convert values.
