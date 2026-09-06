from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Literal

from ..database import get_db
from ..mock_data import simulate_prediction, generate_shap_explanation
import json

router = APIRouter(prefix="/api", tags=["ingest"])


class NewComplaint(BaseModel):
    victim_name: str
    amount: float = Field(ge=0)
    location: str
    complaint_type: str
    status: Literal["Under Review", "Resolved", "Escalated"] = "Under Review"


@router.post("/complaints")
async def create_complaint(payload: NewComplaint, db=Depends(get_db)):
    """Ingest a new complaint and auto-generate a prediction + alert."""
    cur = db.cursor()
    # Default coords for the given location name (mock: use Delhi region if unknown)
    lat, lon = 28.7041, 77.1025
    now = datetime.now().isoformat()
    cur.execute(
        """INSERT INTO complaints (victim_name, amount, status, location, latitude, longitude, complaint_type, timestamp)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (payload.victim_name, payload.amount, payload.status, payload.location,
         lat, lon, payload.complaint_type, now),
    )
    complaint_id = cur.lastrowid

    complaint = {
        "id": complaint_id,
        "amount": payload.amount,
        "status": payload.status,
        "complaint_type": payload.complaint_type,
        "location": payload.location,
    }
    pred = simulate_prediction(complaint)
    cur.execute(
        """INSERT INTO predictions (complaint_id, predicted_lat, predicted_lon, probability, risk_level, predicted_location)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (pred["complaint_id"], pred["predicted_lat"], pred["predicted_lon"],
         pred["probability"], pred["risk_level"], pred["predicted_location"]),
    )

    alert_id = None
    if pred["risk_level"] in ("High", "Medium"):
        shap = generate_shap_explanation(complaint, pred)
        title = f"Predicted Withdrawal — {pred['predicted_location'].split(',')[0]}"
        description = (
            f"Complaint #{complaint_id} ({payload.complaint_type}) flagged as {pred['risk_level']} risk. "
            f"Predicted cash-out at {pred['predicted_location']} with {pred['probability']*100:.0f}% probability."
        )
        cur.execute(
            """INSERT INTO alerts (complaint_id, title, description, risk_level, predicted_location,
               predicted_lat, predicted_lon, probability, shap_explanation, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (complaint_id, title, description, pred["risk_level"],
             pred["predicted_location"], pred["predicted_lat"], pred["predicted_lon"],
             pred["probability"], json.dumps(shap), now),
        )
        alert_id = cur.lastrowid

    return {
        "complaint_id": complaint_id,
        "prediction": pred,
        "alert_id": alert_id,
        "message": "Complaint ingested and prediction generated.",
    }
