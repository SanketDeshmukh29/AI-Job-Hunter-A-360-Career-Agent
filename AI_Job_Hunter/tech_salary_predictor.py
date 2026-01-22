# tech_salary_predictor.py — Robust version (auto-detect salary column)
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor
import joblib
import os

# ----------------- Paths -----------------
DATA_PATH = os.path.join("data", "Tech_Job_Salaries_in_India.csv")
MODEL_PATH = os.path.join("data", "salary_model.pkl")

# ----------------- Train Salary Model -----------------
def train_salary_model(force_retrain=False):
    """Train and save the salary prediction model using the dataset."""
    if os.path.exists(MODEL_PATH) and not force_retrain:
        print("✅ Loaded existing salary model.")
        return joblib.load(MODEL_PATH)

    print("🚀 Training new salary prediction model...")

    df = pd.read_csv(DATA_PATH)
    df.columns = df.columns.str.strip().str.lower()  # Normalize column names

    # Automatically detect salary column
    possible_salary_cols = [c for c in df.columns if "salary" in c or "ctc" in c or "income" in c]
    if not possible_salary_cols:
        raise KeyError("❌ No salary-related column found in dataset.")
    salary_col = possible_salary_cols[0]
    print(f"💰 Using '{salary_col}' as target column.")

    df = df.dropna(subset=[salary_col]).drop_duplicates()
    df = df.rename(columns={salary_col: "salary"})

    # Select relevant columns (those present in dataset)
    potential_features = [
        "job_title", "title", "company", "organization",
        "location", "city", "experience_level", "experience",
        "employment_type", "job_type", "skills", "tech_stack"
    ]
    feature_cols = [col for col in potential_features if col in df.columns]

    if not feature_cols:
        raise ValueError("❌ No valid feature columns found in dataset.")

    df = df[feature_cols + ["salary"]]

    X = df.drop("salary", axis=1)
    y = df["salary"]

    # One-hot encode categorical columns
    cat_cols = X.select_dtypes(include=["object"]).columns
    preprocessor = ColumnTransformer(
        transformers=[("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols)],
        remainder="passthrough"
    )

    # Random Forest model
    model = Pipeline([
        ("preprocessor", preprocessor),
        ("regressor", RandomForestRegressor(n_estimators=300, random_state=42, n_jobs=-1))
    ])

    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model.fit(X_train, y_train)

    # Save trained model
    os.makedirs("data", exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    print(f"✅ Salary model trained and saved at: {MODEL_PATH}")
    print(f"📊 Train size: {X_train.shape}, Test size: {X_test.shape}")
    return model

# ----------------- Predict Salary -----------------
def predict_salary(job_title, company, location, experience_level, employment_type, skills):
    """Predict salary for given job details."""
    if not os.path.exists(MODEL_PATH):
        print("⚙️ Model not found. Training now...")
        model = train_salary_model()
    else:
        model = joblib.load(MODEL_PATH)

    user_df = pd.DataFrame([{
        "job_title": job_title or "",
        "company": company or "",
        "location": location or "",
        "experience_level": experience_level or "Mid",
        "employment_type": employment_type or "Full-Time",
        "skills": skills or ""
    }])

    # Keep only columns known to the model
    try:
        pred = model.predict(user_df)[0]
        return round(float(pred), 2)
    except Exception as e:
        print(f"❌ Prediction error: {e}")
        return "N/A"

# ----------------- CLI Debug/Test -----------------
if __name__ == "__main__":
    print("🧠 Loading/Training model...")
    model = train_salary_model(force_retrain=False)

    # Example prediction
    job_title = "Data Scientist"
    company = "Infosys"
    location = "Pune"
    experience_level = "Mid"
    employment_type = "Full-Time"
    skills = "Python, Machine Learning, SQL"

    print("\n🔮 Predicting salary for sample job:")
    salary = predict_salary(job_title, company, location, experience_level, employment_type, skills)
    print(f"💰 Estimated Salary: ₹{salary} LPA")
