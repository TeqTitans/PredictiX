import random
from datetime import datetime, timedelta

random.seed(42)

INDIAN_CITIES = [
    ("Mumbai", 19.0760, 72.8777),
    ("Delhi", 28.7041, 77.1025),
    ("Bengaluru", 12.9716, 77.5946),
    ("Hyderabad", 17.3850, 78.4867),
    ("Chennai", 13.0827, 80.2707),
    ("Kolkata", 22.5726, 88.3639),
    ("Pune", 18.5204, 73.8567),
    ("Jaipur", 26.9124, 75.7873),
    ("Lucknow", 26.8467, 80.9462),
    ("Surat", 21.1702, 72.8311),
    ("Kochi", 9.9312, 76.2673),
    ("Bhopal", 23.2599, 77.4062),
    ("Patna", 25.5941, 85.1376),
    ("Guwahati", 26.1445, 91.7362),
    ("Nagpur", 21.1458, 79.0882),
    ("Indore", 22.7196, 75.8577),
    ("Chandigarh", 30.7333, 76.7794),
    ("Visakhapatnam", 17.6868, 83.2185),
]

VICTIM_NAMES = [
    "Rahul Sharma", "Priya Patel", "Amit Kumar", "Sneha Reddy", "Vikram Singh",
    "Ananya Gupta", "Rohit Verma", "Deepika Nair", "Karan Mehta", "Pooja Iyer",
    "Arjun Rao", "Nisha Agarwal", "Siddharth Joshi", "Meera Krishnan",
    "Aditya Deshmukh", "Kavya Bhat", "Rajesh Khanna", "Divya Menon",
    "Sanjay Yadav", "Anjali Saxena",
]

COMPLAINT_TYPES = [
    "UPI Fraud", "Phishing Email", "Fake Loan App", "Investment Scam",
    "OTP Fraud", "Job Racket", "Impersonation Scam", "QR Code Fraud",
    "Parcel Customs Scam", "Fake Customer Care",
]

STATUSES = ["Under Review", "Resolved", "Escalated"]

# ATM / cash withdrawal hotspot zones near major cities
HOTSPOT_ZONES = [
    ("Connaught Place ATM Hub, Delhi", 28.6315, 77.2167),
    ("Bandra Linking Road, Mumbai", 19.0596, 72.8295),
    ("MG Road, Bengaluru", 12.9756, 77.6051),
    ("Banjara Hills, Hyderabad", 17.4156, 78.4347),
    ("T Nagar, Chennai", 13.0418, 80.2341),
    ("Park Street, Kolkata", 22.5535, 88.3520),
    ("Hauz Khas, Delhi", 28.5494, 77.2001),
    ("Andheri West, Mumbai", 19.1197, 72.8468),
]


def _random_timestamp(days_back_max=7):
    days_back = random.randint(0, days_back_max)
    hours = random.randint(0, 23)
    minutes = random.randint(0, 59)
    base = datetime(2026, 9, 6, 12, 0, 0) - timedelta(days=days_back, hours=hours, minutes=minutes)
    return base.isoformat()


def generate_complaints(count=20):
    complaints = []
    used_names = random.sample(VICTIM_NAMES, min(count, len(VICTIM_NAMES)))
    for i in range(count):
        city_name, lat, lon = random.choice(INDIAN_CITIES)
        # jitter the coordinates slightly for realism
        lat_jittered = lat + random.uniform(-0.05, 0.05)
        lon_jittered = lon + random.uniform(-0.05, 0.05)
        name = used_names[i] if i < len(used_names) else f"Victim {i+1}"
        complaints.append(
            {
                "victim_name": name,
                "amount": round(random.uniform(5000, 850000), 2),
                "status": random.choices(STATUSES, weights=[0.4, 0.3, 0.3])[0],
                "location": city_name,
                "latitude": round(lat_jittered, 4),
                "longitude": round(lon_jittered, 4),
                "complaint_type": random.choice(COMPLAINT_TYPES),
                "timestamp": _random_timestamp(),
            }
        )
    return complaints


def simulate_prediction(complaint):
    """
    Mock prediction logic.
    Generates a risk score and predicted withdrawal location based on
    complaint attributes.
    """
    amount = complaint["amount"]
    status = complaint["status"]

    # Heuristic-ish mock scoring: higher amount + escalated => higher risk
    base_score = min(amount / 850000, 1.0) * 0.5
    status_boost = {"Escalated": 0.3, "Under Review": 0.15, "Resolved": 0.0}[status]
    noise = random.uniform(-0.1, 0.15)
    probability = max(0.05, min(0.98, round(base_score + status_boost + noise, 3)))

    if probability >= 0.65:
        risk_level = "High"
    elif probability >= 0.35:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    # Predict withdrawal near a hotspot zone
    hotspot = random.choice(HOTSPOT_ZONES)
    predicted_lat = round(hotspot[1] + random.uniform(-0.02, 0.02), 4)
    predicted_lon = round(hotspot[2] + random.uniform(-0.02, 0.02), 4)
    predicted_location = hotspot[0]

    return {
        "complaint_id": complaint["id"],
        "predicted_location": predicted_location,
        "predicted_lat": predicted_lat,
        "predicted_lon": predicted_lon,
        "probability": probability,
        "risk_level": risk_level,
    }


def generate_shap_explanation(complaint, prediction):
    """
    Mock SHAP-style explanation. Returns feature contributions that explain
    why the alert was generated.
    """
    amount = complaint["amount"]
    probability = prediction["probability"]
    factors = []

    # Amount factor
    if amount > 500000:
        factors.append({
            "feature": "Transaction Amount",
            "contribution": round(0.35 + random.uniform(-0.05, 0.05), 3),
            "description": f"Amount ₹{amount:,.0f} exceeds the high-risk threshold of ₹5,00,000",
        })
    elif amount > 100000:
        factors.append({
            "feature": "Transaction Amount",
            "contribution": round(0.20 + random.uniform(-0.03, 0.03), 3),
            "description": f"Amount ₹{amount:,.0f} is above the medium-risk threshold of ₹1,00,000",
        })
    else:
        factors.append({
            "feature": "Transaction Amount",
            "contribution": round(0.08 + random.uniform(-0.02, 0.02), 3),
            "description": f"Amount ₹{amount:,.0f} is within typical fraud range",
        })

    # Status factor
    status = complaint["status"]
    status_contrib = {"Escalated": 0.22, "Under Review": 0.10, "Resolved": -0.05}[status]
    factors.append({
        "feature": "Case Status",
        "contribution": round(status_contrib + random.uniform(-0.02, 0.02), 3),
        "description": f"Case is marked '{status}', indicating {'active threat' if status != 'Resolved' else 'closure'}",
    })

    # Complaint type factor
    ctype = complaint["complaint_type"]
    high_risk_types = ["Investment Scam", "Fake Loan App", "OTP Fraud", "Parcel Customs Scam"]
    type_contrib = 0.18 if ctype in high_risk_types else 0.08
    factors.append({
        "feature": "Complaint Type",
        "contribution": round(type_contrib + random.uniform(-0.03, 0.03), 3),
        "description": f"'{ctype}' is associated with {'rapid cash-out patterns' if ctype in high_risk_types else 'moderate withdrawal activity'}",
    })

    # Proximity to known hotspot
    factors.append({
        "feature": "Geographic Proximity",
        "contribution": round(0.12 + random.uniform(-0.03, 0.03), 3),
        "description": f"Victim location near active fraud withdrawal corridor",
    })

    # Time recency
    factors.append({
        "feature": "Time Recency",
        "contribution": round(0.10 + random.uniform(-0.03, 0.03), 3),
        "description": "Complaint filed within the last 72 hours — cash-out window still open",
    })

    return factors


def generate_alert(complaint, prediction):
    shap = generate_shap_explanation(complaint, prediction)
    risk = prediction["risk_level"]
    title = f"Predicted Withdrawal — {prediction['predicted_location'].split(',')[0]}"
    description = (
        f"Complaint #{complaint['id']} ({complaint['complaint_type']}) flagged as {risk} risk. "
        f"Predicted cash-out at {prediction['predicted_location']} with {prediction['probability']*100:.0f}% probability."
    )
    return {
        "complaint_id": complaint["id"],
        "title": title,
        "description": description,
        "risk_level": risk,
        "predicted_location": prediction["predicted_location"],
        "predicted_lat": prediction["predicted_lat"],
        "predicted_lon": prediction["predicted_lon"],
        "probability": prediction["probability"],
        "shap_explanation": shap,
        "timestamp": _random_timestamp(3),
    }


def generate_hotspots():
    hotspots = []
    for i, (name, lat, lon) in enumerate(HOTSPOT_ZONES):
        hotspots.append(
            {
                "name": name,
                "latitude": lat,
                "longitude": lon,
                "intensity": round(random.uniform(0.55, 0.98), 2),
                "active_cases": random.randint(3, 14),
            }
        )
    return hotspots


def seed_database(conn):
    cur = conn.cursor()
    # Clear existing
    for table in ["alerts", "predictions", "complaints", "hotspots"]:
        cur.execute(f"DELETE FROM {table}")

    complaints_data = generate_complaints(20)
    for c in complaints_data:
        cur.execute(
            """INSERT INTO complaints (victim_name, amount, status, location, latitude, longitude, complaint_type, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (c["victim_name"], c["amount"], c["status"], c["location"],
             c["latitude"], c["longitude"], c["complaint_type"], c["timestamp"]),
        )
        c["id"] = cur.lastrowid

    all_predictions = []
    all_alerts = []
    for c in complaints_data:
        pred = simulate_prediction(c)
        cur.execute(
            """INSERT INTO predictions (complaint_id, predicted_lat, predicted_lon, probability, risk_level, predicted_location)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (pred["complaint_id"], pred["predicted_lat"], pred["predicted_lon"],
             pred["probability"], pred["risk_level"], pred["predicted_location"]),
        )
        pred["id"] = cur.lastrowid
        all_predictions.append(pred)

        # Generate alerts for Medium and High risk
        if pred["risk_level"] in ("High", "Medium"):
            alert = generate_alert(c, pred)
            cur.execute(
                """INSERT INTO alerts (complaint_id, title, description, risk_level, predicted_location,
                   predicted_lat, predicted_lon, probability, shap_explanation, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (alert["complaint_id"], alert["title"], alert["description"],
                 alert["risk_level"], alert["predicted_location"], alert["predicted_lat"],
                 alert["predicted_lon"], alert["probability"],
                 __import__("json").dumps(alert["shap_explanation"]), alert["timestamp"]),
            )
            alert["id"] = cur.lastrowid
            all_alerts.append(alert)

    hotspots_data = generate_hotspots()
    for h in hotspots_data:
        cur.execute(
            """INSERT INTO hotspots (name, latitude, longitude, intensity, active_cases)
               VALUES (?, ?, ?, ?, ?)""",
            (h["name"], h["latitude"], h["longitude"], h["intensity"], h["active_cases"]),
        )
        h["id"] = cur.lastrowid

    return complaints_data, all_predictions, all_alerts, hotspots_data
