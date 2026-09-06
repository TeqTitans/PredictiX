from pydantic import BaseModel, Field
from typing import Literal, List, Optional
from datetime import datetime

class Top3Location(BaseModel):
    rank: int
    name: str
    lat: float
    lon: float
    probability: float
    distance_km: float
    estimated_cashout_window: str

class Complaint(BaseModel):
    id: int
    victim_name: str
    victim_phone: Optional[str] = "+91 98765 43210"
    victim_age: Optional[int] = 45
    amount: float
    status: Literal["Under Review", "Resolved", "Escalated"]
    location: str
    latitude: float
    longitude: float
    complaint_type: str
    timestamp: str

class NewComplaint(BaseModel):
    victim_name: str
    victim_phone: Optional[str] = "+91 98765 43210"
    victim_age: Optional[int] = 45
    amount: float = Field(ge=0)
    location: str
    latitude: Optional[float] = 28.7041
    longitude: Optional[float] = 77.1025
    complaint_type: str
    status: Literal["Under Review", "Resolved", "Escalated"] = "Under Review"

class Prediction(BaseModel):
    complaint_id: int
    predicted_location: str
    predicted_lat: float
    predicted_lon: float
    probability: float
    risk_level: Literal["High", "Medium", "Low"]
    top3_locations: Optional[List[Top3Location]] = []

class ShapFactor(BaseModel):
    feature: str
    contribution: float
    description: str

class Alert(BaseModel):
    id: int
    complaint_id: int
    title: str
    description: str
    risk_level: Literal["High", "Medium", "Low"]
    predicted_location: str
    predicted_lat: float
    predicted_lon: float
    probability: float
    shap_explanation: List[ShapFactor]
    timestamp: str
    dispatch_status: Optional[str] = "Pending"
    countdown_seconds: Optional[int] = 1080
    nearest_police_station: Optional[str] = "Andheri East Police Station"
    bank_notified: Optional[bool] = True
    assigned_constable: Optional[str] = "Constable R. Shinde (PCR-14)"

class Hotspot(BaseModel):
    id: int
    name: str
    latitude: float
    longitude: float
    intensity: float
    active_cases: int

class KPIData(BaseModel):
    total_complaints: int
    high_risk_alerts: int
    predicted_withdrawals: int
    recovery_rate: float

class TrendPoint(BaseModel):
    date: str
    complaints: int
    resolved: int

class DispatchSMSRequest(BaseModel):
    alert_id: int
    recipient_type: Literal["constable", "sho", "bank_manager"] = "constable"
    phone_number: Optional[str] = "+91 98123 45678"

class AlertStatusUpdate(BaseModel):
    status: Literal["Pending", "Dispatched", "Constable En Route", "ATM Intercepted", "Mule Apprehended", "Cleared"]

class FreezeATMRequest(BaseModel):
    atm_name: str
    frozen: bool

class FamilyVerifyRequest(BaseModel):
    transaction_id: str
    approve: bool
    reason: Optional[str] = ""
