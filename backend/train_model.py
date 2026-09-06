import os
import random
import numpy as np
import pandas as pd
import joblib
from xgboost import XGBClassifier
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

# Ensure directory exists for binary models
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models_bin")
os.makedirs(MODEL_DIR, exist_ok=True)

# ATM Hotspot hubs in major Indian Metro Regions
HOTSPOT_HUBS = [
    {"name": "SBI ATM Hub, Connaught Place, Delhi", "lat": 28.6315, "lon": 77.2167, "city": "Delhi"},
    {"name": "HDFC ATM, Bandra Linking Road, Mumbai", "lat": 19.0596, "lon": 72.8295, "city": "Mumbai"},
    {"name": "ICICI Branch ATM, MG Road, Bengaluru", "lat": 12.9756, "lon": 77.6051, "city": "Bengaluru"},
    {"name": "Axis Bank ATM, Banjara Hills, Hyderabad", "lat": 17.4156, "lon": 78.4347, "city": "Hyderabad"},
    {"name": "SBI ATM, T Nagar, Chennai", "lat": 13.0418, "lon": 80.2341, "city": "Chennai"},
    {"name": "Punjab National ATM, Park Street, Kolkata", "lat": 22.5535, "lon": 88.3520, "city": "Kolkata"},
    {"name": "Canara ATM, Hauz Khas, Delhi", "lat": 28.5494, "lon": 77.2001, "city": "Delhi"},
    {"name": "Kotak Mahindra ATM, Andheri West, Mumbai", "lat": 19.1197, "lon": 72.8468, "city": "Mumbai"},
    {"name": "Union Bank ATM, Kothrud, Pune", "lat": 18.5074, "lon": 73.8077, "city": "Pune"},
    {"name": "Bank of Baroda ATM, C-Scheme, Jaipur", "lat": 26.9089, "lon": 75.8012, "city": "Jaipur"}
]

COMPLAINT_TYPE_RISK = {
    "OTP Fraud": 0.85,
    "UPI Fraud": 0.75,
    "Fake Loan App": 0.80,
    "Investment Scam": 0.70,
    "Parcel Customs Scam": 0.90,
    "Impersonation Scam": 0.65,
    "Fake Customer Care": 0.60,
    "Job Racket": 0.50,
    "Phishing Email": 0.40,
    "QR Code Fraud": 0.55
}

def generate_training_data(n_samples=600):
    np.random.seed(42)
    random.seed(42)
    
    data = []
    coords = []
    
    types = list(COMPLAINT_TYPE_RISK.keys())
    
    for i in range(n_samples):
        ctype = random.choice(types)
        type_base = COMPLAINT_TYPE_RISK[ctype]
        
        # Log-normal distribution for amounts
        amount = round(float(np.random.lognormal(11.2, 1.0)), 2)
        amount = max(2000.0, min(amount, 1200000.0))
        
        # Status
        status = random.choices(["Under Review", "Escalated", "Resolved"], weights=[0.5, 0.35, 0.15])[0]
        status_num = 2 if status == "Escalated" else (1 if status == "Under Review" else 0)
        
        # Victim age
        victim_age = random.randint(19, 78)
        elderly_factor = 1 if victim_age >= 60 else 0
        
        # Recency in hours (0.1h to 72h)
        recency_hours = round(random.uniform(0.1, 72.0), 2)
        recency_factor = 1.0 if recency_hours < 2.0 else (0.6 if recency_hours < 12.0 else 0.2)
        
        # Select city hub and add Gaussian noise for coordinates
        hub = random.choice(HOTSPOT_HUBS)
        lat = hub["lat"] + np.random.normal(0, 0.02)
        lon = hub["lon"] + np.random.normal(0, 0.02)
        coords.append([lat, lon])
        
        # Risk probability formula for ground truth label
        risk_score = (
            0.35 * type_base +
            0.30 * min(amount / 500000.0, 1.0) +
            0.15 * status_num / 2.0 +
            0.10 * recency_factor +
            0.10 * (1.2 if elderly_factor else 0.8)
        )
        risk_score += np.random.normal(0, 0.05)
        risk_score = max(0.0, min(1.0, risk_score))
        
        label = 1 if risk_score >= 0.55 else 0
        
        data.append({
            "amount": amount,
            "complaint_type_score": type_base,
            "status_num": status_num,
            "victim_age": victim_age,
            "recency_hours": recency_hours,
            "latitude": lat,
            "longitude": lon,
            "risk_score": risk_score,
            "label": label
        })
        
    df = pd.DataFrame(data)
    coords_np = np.array(coords)
    return df, coords_np

def train_and_save():
    print("[TRAIN] Generating synthetic complaint dataset...")
    df, coords = generate_training_data(600)
    
    # 1. Feature matrix for XGBoost
    feature_cols = ["amount", "complaint_type_score", "status_num", "victim_age", "recency_hours", "latitude", "longitude"]
    X = df[feature_cols]
    y = df["label"]
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    print("[TRAIN] Fitting XGBoost Classifier...")
    model = XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.08,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric="logloss"
    )
    model.fit(X_scaled, y)
    
    # 2. DBSCAN geospatial clustering (kms eps ~ 5km -> 0.045 deg)
    print("[TRAIN] Fitting DBSCAN Geospatial Clustering...")
    dbscan = DBSCAN(eps=0.045, min_samples=3)
    dbscan.fit(coords)
    
    # Calculate cluster centroids
    df["cluster"] = dbscan.labels_
    cluster_centroids = []
    for c_id in set(dbscan.labels_):
        if c_id == -1:
            continue  # noise
        sub = df[df["cluster"] == c_id]
        centroid_lat = float(sub["latitude"].mean())
        centroid_lon = float(sub["longitude"].mean())
        count = len(sub)
        
        # Match nearest hotspot hub for naming
        best_hub = HOTSPOT_HUBS[0]
        min_dist = 999.0
        for h in HOTSPOT_HUBS:
            d = ((h["lat"] - centroid_lat)**2 + (h["lon"] - centroid_lon)**2)**0.5
            if d < min_dist:
                min_dist = d
                best_hub = h
                
        cluster_centroids.append({
            "cluster_id": int(c_id),
            "name": f"{best_hub['name']} Sector {c_id+1}",
            "lat": centroid_lat,
            "lon": centroid_lon,
            "count": count,
            "city": best_hub["city"]
        })
        
    # Save artifacts
    print("[TRAIN] Saving Joblib model binaries...")
    joblib.dump(model, os.path.join(MODEL_DIR, "xgb_model.joblib"))
    joblib.dump(scaler, os.path.join(MODEL_DIR, "scaler.joblib"))
    joblib.dump(dbscan, os.path.join(MODEL_DIR, "dbscan_model.joblib"))
    joblib.dump(cluster_centroids, os.path.join(MODEL_DIR, "hotspot_centroids.joblib"))
    joblib.dump(HOTSPOT_HUBS, os.path.join(MODEL_DIR, "hotspot_hubs.joblib"))
    
    print(f"[SUCCESS] Trained models successfully saved to {MODEL_DIR}")
    print(f"   XGBoost trained on {len(df)} samples")
    print(f"   DBSCAN identified {len(cluster_centroids)} high-density withdrawal clusters")

if __name__ == "__main__":
    train_and_save()
