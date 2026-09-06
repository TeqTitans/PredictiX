import random
import json
from datetime import datetime, timedelta
from .ai_engine import ai_engine

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
]

VICTIM_NAMES = [
    "Rahul Sharma", "Priya Patel", "Amit Kumar", "Sneha Reddy", "Vikram Singh",
    "Ananya Gupta", "Rohit Verma", "Deepika Nair", "Karan Mehta", "Pooja Iyer",
    "Arjun Rao", "Nisha Agarwal", "Siddharth Joshi", "Meera Krishnan",
    "Aditya Deshmukh", "Kavya Bhat", "Rajesh Khanna", "Divya Menon",
    "Sanjay Yadav", "Anjali Saxena", "Ramesh Chawla", "Sunita Mahajan"
]

COMPLAINT_TYPES = [
    "UPI Fraud", "OTP Fraud", "Fake Loan App", "Investment Scam",
    "Parcel Customs Scam", "Impersonation Scam", "Fake Customer Care",
    "QR Code Fraud", "Job Racket", "Phishing Email"
]

STATUSES = ["Under Review", "Escalated", "Resolved"]

HOTSPOT_ZONES = [
    ("Connaught Place ATM Hub, Delhi", 28.6315, 77.2167),
    ("Bandra Linking Road ATM, Mumbai", 19.0596, 72.8295),
    ("MG Road Bank Corridor, Bengaluru", 12.9756, 77.6051),
    ("Banjara Hills ATM Sector, Hyderabad", 17.4156, 78.4347),
    ("T Nagar Financial ATM, Chennai", 13.0418, 80.2341),
    ("Park Street Branch ATM, Kolkata", 22.5535, 88.3520),
    ("Hauz Khas Commercial Hub, Delhi", 28.5494, 77.2001),
    ("Andheri West ATM Hub, Mumbai", 19.1197, 72.8468),
]

POLICE_STATIONS = [
    "Andheri East Police Station, Mumbai",
    "Connaught Place PCR Station, Delhi",
    "Cubbon Park Police Station, Bengaluru",
    "Banjara Hills Cyber Police Unit, Hyderabad",
    "T Nagar Cyber Crime Cell, Chennai",
    "Park Street Police Station, Kolkata",
    "Shivajinagar Police Station, Pune"
]

CONSTABLES = [
    "Constable R. Shinde (PCR-14)",
    "Constable V. Pawar (PCR-08)",
    "Constable S. Yadav (PCR-22)",
    "Constable M. Reddy (PCR-05)",
    "Constable A. Singh (PCR-11)"
]

def _random_timestamp(days_back_max=7):
    days_back = random.randint(0, days_back_max)
    hours = random.randint(0, 23)
    minutes = random.randint(0, 59)
    base = datetime(2026, 9, 6, 12, 0, 0) - timedelta(days=days_back, hours=hours, minutes=minutes)
    return base.isoformat()

def generate_complaints(count=24):
    complaints = []
    used_names = random.sample(VICTIM_NAMES, min(count, len(VICTIM_NAMES)))
    for i in range(count):
        city_name, lat, lon = random.choice(INDIAN_CITIES)
        lat_jittered = round(lat + random.uniform(-0.04, 0.04), 4)
        lon_jittered = round(lon + random.uniform(-0.04, 0.04), 4)
        name = used_names[i] if i < len(used_names) else f"Victim {i+1}"
        phone = f"+91 {random.randint(70000, 99999)} {random.randint(10000, 99999)}"
        age = random.randint(22, 76)
        
        complaints.append({
            "victim_name": name,
            "victim_phone": phone,
            "victim_age": age,
            "amount": round(random.uniform(8000, 850000), 2),
            "status": random.choices(STATUSES, weights=[0.45, 0.40, 0.15])[0],
            "location": city_name,
            "latitude": lat_jittered,
            "longitude": lon_jittered,
            "complaint_type": random.choice(COMPLAINT_TYPES),
            "timestamp": _random_timestamp(),
        })
    return complaints

def seed_database(conn):
    cur = conn.cursor()
    for table in ["alerts", "predictions", "complaints", "hotspots", "retraining_history"]:
        cur.execute(f"DELETE FROM {table}")

    complaints_data = generate_complaints(24)
    for c in complaints_data:
        cur.execute(
            """INSERT INTO complaints (victim_name, victim_phone, victim_age, amount, status, location, latitude, longitude, complaint_type, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (c["victim_name"], c["victim_phone"], c["victim_age"], c["amount"], c["status"],
             c["location"], c["latitude"], c["longitude"], c["complaint_type"], c["timestamp"]),
        )
        c["id"] = cur.lastrowid

    all_predictions = []
    all_alerts = []
    
    for c in complaints_data:
        res = ai_engine.predict(c)
        cur.execute(
            """INSERT INTO predictions (complaint_id, predicted_lat, predicted_lon, probability, risk_level, predicted_location, top3_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (c["id"], res["predicted_lat"], res["predicted_lon"], res["probability"],
             res["risk_level"], res["predicted_location"], json.dumps(res["top3_locations"])),
        )
        pred_id = cur.lastrowid

        if res["risk_level"] in ("High", "Medium"):
            title = f"Predicted Cash-Out — {res['predicted_location'].split(',')[0]}"
            description = (
                f"Complaint #{c['id']} ({c['victim_name']} — {c['complaint_type']}, ₹{c['amount']:,.0f}) flagged as {res['risk_level']} Risk. "
                f"Top 1 predicted cash-out target: {res['predicted_location']} ({res['probability']*100:.0f}% confidence)."
            )
            station = random.choice(POLICE_STATIONS)
            constable = random.choice(CONSTABLES)
            countdown = res["countdown_mins"] * 60
            
            cur.execute(
                """INSERT INTO alerts (complaint_id, title, description, risk_level, predicted_location,
                   predicted_lat, predicted_lon, probability, shap_explanation, timestamp,
                   dispatch_status, countdown_seconds, nearest_police_station, bank_notified, assigned_constable)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (c["id"], title, description, res["risk_level"], res["predicted_location"],
                 res["predicted_lat"], res["predicted_lon"], res["probability"],
                 json.dumps(res["shap_explanation"]), c["timestamp"],
                 "Pending", countdown, station, 1, constable),
            )
            alert_id = cur.lastrowid
            all_alerts.append(alert_id)

    # Seed Hotspot Zones
    for name, lat, lon in HOTSPOT_ZONES:
        intensity = round(random.uniform(0.62, 0.96), 2)
        active_cases = random.randint(4, 18)
        cur.execute(
            """INSERT INTO hotspots (name, latitude, longitude, intensity, active_cases)
               VALUES (?, ?, ?, ?, ?)""",
            (name, lat, lon, intensity, active_cases),
        )

    # Seed Retraining History
    cur.execute(
        """INSERT INTO retraining_history (trained_at, dataset_size, accuracy, precision_score, status)
           VALUES (?, ?, ?, ?, ?)""",
        (datetime.now().isoformat(), 600, 0.942, 0.918, "Success"),
    )

    print(f"[MOCK SEED] Successfully seeded DB with {len(complaints_data)} complaints & {len(all_alerts)} AI alerts.")
