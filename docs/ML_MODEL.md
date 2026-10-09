# ML model

`train_model.py` validates the required columns and builds a scikit-learn `Pipeline` with a `ColumnTransformer`: source, destination, and transportation use `OneHotEncoder(handle_unknown="ignore")`; travelers and days use `StandardScaler`; a multi-output `RandomForestRegressor` predicts transport, accommodation, food, and other expenses.

A seeded 75/25 holdout split is used to calculate MAE, MSE, RMSE, and R-squared. The pipeline is then refit on all valid rows and saved as a complete artifact. Admin training writes a new artifact under `models/`, stores metrics in `model_versions`, and activates it only after training succeeds. Existing artifacts are retained and can be reactivated.

The bundled data has 58 rows, with 57 complete rows in the current artifact. Its recorded holdout metrics (MAE about 254.44, MSE about 131,695.38, R-squared about 0.767) are a small-sample demonstration, not a production performance claim. Feature importance is impurity based and describes model reliance, not causation. No confidence interval is claimed.

Inputs are source, destination, transportation, travelers, and days. Season, distance, accommodation category, travel type, and daily actuals are absent from the source data and are not used as model features.
