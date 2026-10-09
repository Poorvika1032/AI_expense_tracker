# Routes and JSON API

## User HTML routes

`/`, `/register`, `/login`, `/logout` (POST), `/dashboard`, `/predict` (POST), `/history`, `/trips/<id>`, `/trips/<id>/edit` (POST), `/trips/<id>/duplicate` (POST), `/trips/<id>/delete` (POST), `/trips/<id>/expenses` (POST), `/expenses/<id>/edit` (POST), `/expenses/<id>/delete` (POST), `/analytics`, `/reports`, `/reports/export.csv`, `/reports/export.pdf`, `/reports/export.xlsx`, `/insights`, `/model-performance`, `/model-insights`, `/what-if`, `/optimize`, `/profile`, `/currency-converter`, `/wishlist`, `/wishlist/<id>/delete` (POST), `/favorites`, `/favorites/toggle/<trip_id>` (POST), `/recommendations`, `/compare`, `/itinerary`, `/trips/<id>/daily-forecast`, `/notifications`, `/notifications/<id>/read` (POST).

## Admin HTML routes

`/admin`, `/admin/users`, `/admin/users/<id>/toggle` (POST), `/admin/users/<id>/delete` (POST), `/admin/dataset`, `/admin/model/train` (POST), `/admin/models`, `/admin/models/<id>/activate` (POST), and `/admin/logs`. Every route checks the ADMIN role.

## JSON API

All API routes require login and use the same JSON envelope `{ "success": true, "data": ... }` or `{ "success": false, "error": ... }`.

- `GET /api/csrf` returns the session CSRF token.
- `POST /api/predict` accepts source, destination, travelers, days, and budget and returns transport estimates and the budget-aware choice.
- `POST /api/what-if` accepts source, destination, travelers, and days and returns mode/duration scenarios.
- `POST /api/currency-convert` converts using a cached daily reference rate.
- `GET /api/dashboard-stats` returns only the signed-in user's aggregate totals.

Reports and analytics accept `date_from` and `date_to` query parameters.

For JSON POST requests, send `X-CSRF-Token` with the token returned by `/api/csrf`.
