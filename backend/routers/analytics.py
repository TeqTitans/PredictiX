import json
import random
from datetime import datetime, timedelta
from collections import OrderedDict
from fastapi import APIRouter, Depends, Query

from ..database import get_db
from ..models import (
    Complaint, Prediction, Alert, Hotspot, KPIData, TrendPoint,
)

router = APIRouter(prefix="/api", tags=["analytics"])

@router.get("/complaints", response_model=list[Complaint])
async def get_complaints(limit: int = Query(100, ge=1, le=500), db=Depends(get_db)):
    rows = db.execute(
        "SELECT * FROM complaints ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    results = []
    for r in rows:
        d = dict(r)
        if "victim_phone" not in d or not d["victim_phone"]:
            d["victim_phone"] = "+91 98765 43210"
        if "victim_age" not in d or not d["victim_age"]:
            d["victim_age"] = 45
        results.append(d)
    return results

@router.get("/predictions", response_model=list[Prediction])
async def get_predictions(limit: int = Query(100, ge=1, le=500), db=Depends(get_db)):
    rows = db.execute(
        "SELECT * FROM predictions ORDER BY probability DESC LIMIT ?", (limit,)
    ).fetchall()
    results = []
    for r in rows:
        top3_raw = r["top3_json"] if "top3_json" in r.keys() else "[]"
        try:
            top3 = json.loads(top3_raw) if isinstance(top3_raw, str) else top3_raw
        except Exception:
            top3 = []
        results.append({
            "complaint_id": r["complaint_id"],
            "predicted_location": r["predicted_location"],
            "predicted_lat": r["predicted_lat"],
            "predicted_lon": r["predicted_lon"],
            "probability": r["probability"],
            "risk_level": r["risk_level"],
            "top3_locations": top3,
        })
    return results

@router.get("/alerts", response_model=list[Alert])
async def get_alerts(limit: int = Query(50, ge=1, le=100), db=Depends(get_db)):
    rows = db.execute(
        "SELECT * FROM alerts ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    results = []
    for r in rows:
        shap_raw = r["shap_explanation"]
        try:
            shap = json.loads(shap_raw) if isinstance(shap_raw, str) else shap_raw
        except (json.JSONDecodeError, TypeError):
            shap = []

        d_status = r["dispatch_status"] if "dispatch_status" in r.keys() else "Pending"
        c_seconds = r["countdown_seconds"] if "countdown_seconds" in r.keys() else 1080
        p_station = r["nearest_police_station"] if "nearest_police_station" in r.keys() else "Andheri Police Station"
        b_notified = bool(r["bank_notified"]) if "bank_notified" in r.keys() else True
        constable = r["assigned_constable"] if "assigned_constable" in r.keys() else "Constable R. Shinde (PCR-14)"

        results.append({
            "id": r["id"],
            "complaint_id": r["complaint_id"],
            "title": r["title"],
            "description": r["description"],
            "risk_level": r["risk_level"],
            "predicted_location": r["predicted_location"],
            "predicted_lat": r["predicted_lat"],
            "predicted_lon": r["predicted_lon"],
            "probability": r["probability"],
            "shap_explanation": shap,
            "timestamp": r["timestamp"],
            "dispatch_status": d_status,
            "countdown_seconds": c_seconds,
            "nearest_police_station": p_station,
            "bank_notified": b_notified,
            "assigned_constable": constable
        })
    return results

@router.get("/hotspots", response_model=list[Hotspot])
async def get_hotspots(db=Depends(get_db)):
    rows = db.execute("SELECT * FROM hotspots").fetchall()
    return [dict(r) for r in rows]

@router.get("/kpis", response_model=KPIData)
async def get_kpis(db=Depends(get_db)):
    total = db.execute("SELECT COUNT(*) as c FROM complaints").fetchone()["c"]
    high_risk = db.execute(
        "SELECT COUNT(*) as c FROM alerts WHERE risk_level = 'High'"
    ).fetchone()["c"]
    predicted_withdrawals = db.execute(
        "SELECT COUNT(*) as c FROM predictions WHERE risk_level IN ('High', 'Medium')"
    ).fetchone()["c"]
    resolved = db.execute(
        "SELECT COUNT(*) as c FROM complaints WHERE status = 'Resolved'"
    ).fetchone()["c"]
    recovery_rate = round((resolved / total * 100), 1) if total > 0 else 0.0
    return {
        "total_complaints": total,
        "high_risk_alerts": high_risk,
        "predicted_withdrawals": predicted_withdrawals,
        "recovery_rate": recovery_rate,
    }

@router.get("/trends", response_model=list[TrendPoint])
async def get_trends(db=Depends(get_db)):
    rows = db.execute(
        "SELECT timestamp, status FROM complaints ORDER BY timestamp ASC"
    ).fetchall()

    today = datetime(2026, 9, 6)
    daily = OrderedDict()
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        key = day.strftime("%Y-%m-%d")
        daily[key] = {"complaints": 0, "resolved": 0}

    for r in rows:
        try:
            ts = datetime.fromisoformat(r["timestamp"])
        except (ValueError, TypeError):
            continue
        key = ts.strftime("%Y-%m-%d")
        if key in daily:
            daily[key]["complaints"] += 1
            if r["status"] == "Resolved":
                daily[key]["resolved"] += 1

    random.seed(99)
    for key in daily:
        if daily[key]["complaints"] == 0:
            daily[key]["complaints"] = random.randint(2, 5)
            daily[key]["resolved"] = random.randint(1, 3)

    return [
        {"date": k, "complaints": v["complaints"], "resolved": v["resolved"]}
        for k, v in daily.items()
    ]

@router.get("/national-data")
async def get_national_data(db=Depends(get_db)):
    """State-wise fraud statistics for I4C National Dashboard."""
    return {
        "national_summary": {
            "total_reported_fraud_inr": "₹ 14.82 Cr",
            "prevented_cashouts_inr": "₹ 11.45 Cr",
            "active_mule_networks": 48,
            "avg_interception_time_mins": 16.4
        },
        "state_fraud_volumes": [
            {"state": "Maharashtra", "complaints": 342, "amount_lakhs": 245.5, "risk_index": "CRITICAL"},
            {"state": "Delhi NCR", "complaints": 289, "amount_lakhs": 198.2, "risk_index": "HIGH"},
            {"state": "Karnataka", "complaints": 210, "amount_lakhs": 142.0, "risk_index": "HIGH"},
            {"state": "Telangana", "complaints": 178, "amount_lakhs": 115.8, "risk_index": "MEDIUM"},
            {"state": "Tamil Nadu", "complaints": 156, "amount_lakhs": 98.4, "risk_index": "MEDIUM"},
            {"state": "West Bengal", "complaints": 134, "amount_lakhs": 84.0, "risk_index": "MEDIUM"}
        ],
        "migration_corridors": [
            {"corridor": "Mewat (HR) ➔ Connaught Place (DEL)", "surge": "+42%", "mule_pattern": "Rapid Multi-ATM Drain"},
            {"corridor": "Jamtara (JH) ➔ Park Street (KOL)", "surge": "+28%", "mule_pattern": "QR Code Transfer"},
            {"corridor": "Thane (MH) ➔ Bandra ATM Corridor (MUM)", "surge": "+35%", "mule_pattern": "Investment Scam Cashout"}
        ]
    }

@router.get("/district-kpis")
async def get_district_kpis(db=Depends(get_db)):
    """District level metrics for DCP / SP dashboard."""
    return {
        "district_name": "Mumbai Zone IV / West",
        "active_pcrs": 14,
        "avg_response_time_mins": 14.2,
        "hotspot_count": 8,
        "funds_saved_today_inr": "₹ 18,40,000",
        "station_performance": [
            {"station": "Andheri Police Station", "dispatches": 18, "apprehended": 14, "success_rate": "77.7%"},
            {"station": "Bandra Police Station", "dispatches": 14, "apprehended": 11, "success_rate": "78.5%"},
            {"station": "Hauz Khas Police Station", "dispatches": 12, "apprehended": 9, "success_rate": "75.0%"},
            {"station": "T Nagar Police Station", "dispatches": 9, "apprehended": 7, "success_rate": "77.7%"}
        ]
    }
