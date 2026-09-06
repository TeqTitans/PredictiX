import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from ..database import get_db
from ..models import NewComplaint
from ..ai_engine import ai_engine

router = APIRouter(prefix="/api", tags=["ingest"])

@router.post("/complaints")
async def create_complaint(payload: NewComplaint, db=Depends(get_db)):
    """
    Ingest a new cybercrime complaint into CashTrap.
    Calls AI Prediction Engine (XGBoost + DBSCAN + SHAP) to:
    1. Calculate risk score & risk level.
    2. Forecast Top 3 withdrawal ATM locations with confidence probabilities.
    3. Generate SHAP feature importance breakdown.
    4. Auto-generate Alert and SMS dispatch payload for police PCR.
    """
    cur = db.cursor()
    now = datetime.now().isoformat()
    lat = payload.latitude if payload.latitude else 28.7041
    lon = payload.longitude if payload.longitude else 77.1025

    cur.execute(
        """INSERT INTO complaints (victim_name, victim_phone, victim_age, amount, status, location, latitude, longitude, complaint_type, timestamp)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (payload.victim_name, payload.victim_phone, payload.victim_age, payload.amount,
         payload.status, payload.location, lat, lon, payload.complaint_type, now),
    )
    complaint_id = cur.lastrowid

    complaint_dict = {
        "id": complaint_id,
        "victim_name": payload.victim_name,
        "victim_phone": payload.victim_phone,
        "victim_age": payload.victim_age,
        "amount": payload.amount,
        "status": payload.status,
        "location": payload.location,
        "latitude": lat,
        "longitude": lon,
        "complaint_type": payload.complaint_type,
        "timestamp": now
    }

    # Run AI Engine Prediction
    res = ai_engine.predict(complaint_dict)

    # Save Prediction with Top 3 Locations JSON
    cur.execute(
        """INSERT INTO predictions (complaint_id, predicted_lat, predicted_lon, probability, risk_level, predicted_location, top3_json)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (complaint_id, res["predicted_lat"], res["predicted_lon"], res["probability"],
         res["risk_level"], res["predicted_location"], json.dumps(res["top3_locations"])),
    )
    pred_id = cur.lastrowid

    alert_id = None
    sms_payload = None

    if res["risk_level"] in ("High", "Medium"):
        title = f"Predicted Cash-Out — {res['predicted_location'].split(',')[0]}"
        description = (
            f"Complaint #{complaint_id} ({payload.victim_name} — {payload.complaint_type}, ₹{payload.amount:,.0f}) flagged as {res['risk_level']} Risk. "
            f"Top 1 predicted cash-out target: {res['predicted_location']} ({res['probability']*100:.0f}% confidence)."
        )
        station = f"{payload.location} Central Cyber Police Station"
        constable = "Constable R. Shinde (PCR-14)"
        countdown = res["countdown_mins"] * 60

        cur.execute(
            """INSERT INTO alerts (complaint_id, title, description, risk_level, predicted_location,
               predicted_lat, predicted_lon, probability, shap_explanation, timestamp,
               dispatch_status, countdown_seconds, nearest_police_station, bank_notified, assigned_constable)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (complaint_id, title, description, res["risk_level"], res["predicted_location"],
             res["predicted_lat"], res["predicted_lon"], res["probability"],
             json.dumps(res["shap_explanation"]), now,
             "Pending", countdown, station, 1, constable),
        )
        alert_id = cur.lastrowid

        # Generate SMS alert payload text
        sms_payload = (
            f"🚨 CASHTRAP POLICE DISPATCH ALERT 🚨\n"
            f"REF: ALERT #{alert_id} | COMPLAINT #{complaint_id}\n"
            f"TARGET: {res['predicted_location']}\n"
            f"RISK: {res['risk_level'].upper()} ({res['probability']*100:.0f}% prob)\n"
            f"EST. CASH-OUT WINDOW: {res['countdown_mins']} MINS\n"
            f"ACTION: Dispatch PCR unit immediately. Contact local branch manager."
        )

    # Optional OpenRouter AI Intelligence call
    intel_report = await ai_engine.call_openrouter_intel(complaint_dict, res)

    return {
        "complaint_id": complaint_id,
        "prediction_id": pred_id,
        "alert_id": alert_id,
        "prediction": res,
        "sms_payload": sms_payload,
        "intel_report": intel_report,
        "message": f"Complaint #{complaint_id} successfully processed through CashTrap AI Engine."
    }
