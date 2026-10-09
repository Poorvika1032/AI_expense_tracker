"""Train and persist the travel expense preprocessing + Random Forest pipeline."""
from pathlib import Path
import pickle

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "dataset" / "travel_expense.csv"
MODEL_PATH = ROOT / "travel_expense_model.pkl"
FEATURES = ["source", "destination", "transportation", "travelers", "days"]
TARGETS = ["transport_cost", "accommodation_cost", "food_cost", "other_expenses"]


def train(data_path=DATA_PATH, model_path=MODEL_PATH):
    """Train and save the full inference pipeline from a validated CSV dataset."""
    data_path = Path(data_path)
    model_path = Path(model_path)
    data = pd.read_csv(data_path)
    missing = set(FEATURES + TARGETS) - set(data.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {', '.join(sorted(missing))}")
    data = data[FEATURES + TARGETS].dropna()
    if len(data) < 4:
        raise ValueError("At least four complete dataset rows are required to train the model.")

    prep = ColumnTransformer([
        ("places_transport", OneHotEncoder(handle_unknown="ignore"), FEATURES[:3]),
        ("numeric", StandardScaler(), FEATURES[3:]),
    ])
    model = Pipeline([
        ("preprocessing", prep),
        ("regressor", RandomForestRegressor(n_estimators=200, min_samples_leaf=1,
                                             random_state=42, n_jobs=-1)),
    ])
    x_train, x_test, y_train, y_test = train_test_split(
        data[FEATURES], data[TARGETS], test_size=0.25, random_state=42
    )
    model.fit(x_train, y_train)
    predicted = model.predict(x_test)
    metrics = {
        "dataset_size": int(len(data)),
        "mae": float(mean_absolute_error(y_test, predicted)),
        "mse": float(mean_squared_error(y_test, predicted)),
        "rmse": float(mean_squared_error(y_test, predicted) ** 0.5),
        "r2": float(r2_score(y_test, predicted, multioutput="uniform_average")),
        "trained_at": pd.Timestamp.now("UTC").isoformat(),
    }
    # Refit on all valid rows after evaluation to maximize production training data.
    model.fit(data[FEATURES], data[TARGETS])
    model_path.parent.mkdir(parents=True, exist_ok=True)
    with model_path.open("wb") as file:
        pickle.dump({"pipeline": model, "metrics": metrics, "features": FEATURES,
                     "targets": TARGETS, "trained_at": pd.Timestamp.now("UTC").isoformat()}, file)
    print(f"Saved pipeline to {model_path}")
    print("Evaluation:", metrics)
    return metrics


if __name__ == "__main__":
    train()
