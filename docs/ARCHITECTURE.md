# Architecture

This remains a compact Flask application to preserve the original `python app.py` workflow and existing data. SQLite initialization is additive. Prediction is performed by a persisted sklearn Pipeline loaded once at startup; admin retraining adds versioned artifacts and selects one active model path. Uploaded datasets are CSV only, size-limited, and read as tabular data.

## Main flows

- Registration and login save/check Werkzeug password hashes. Registration cannot choose a role. Admin status is assigned using the CLI and checked on every admin endpoint.
- Trip prediction validates its inputs, runs the same saved model pipeline for transport modes, selects a lowest-cost option that fits the budget when possible, and saves a trip to the current user.
- Actual expenses are linked to the user and trip. Reads, edits, and deletes check both the signed-in user and object ownership.
- What-if and optimization compare model outputs for changed modes/durations. The optimizer does not reduce travelers. Saved savings are labeled as modeled potential reductions.
- Reports distinguish predicted trip totals from recorded actual expenses. Error metrics omit trips with no actual entries.
- Admin dataset/model flows validate CSV structure, persist model metrics, retain old artifacts, and allow activation of an existing version.

All mutating forms require a session CSRF token. SQL values are parameterized; the history sort clause is selected only from a fixed whitelist. Uploaded filenames are not used as storage paths.

## Known model boundary

The trained model uses only source, destination, transportation, traveler count, and days because those are the features available in the bundled CSV. Date ranges are stored for planning and upcoming notifications but are not predictive features. It cannot estimate season, accommodation class, distance, or daily category forecasts from current training data. The itinerary is labeled rule-based. Prediction intervals are not shown.
