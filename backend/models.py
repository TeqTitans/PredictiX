from pydantic import BaseModel, Field
from typing import Literal, List, Optional
from datetime import datetime


class Complaint(BaseModel):
    id: int
    victim_name: str
    amount: float
    status: Literal["Under Review", "Resolved", "Escalated"]
    location: str
    latitude: float
    longitude: float
    complaint_type: str
    timestamp: str


class Prediction(BaseModel):
    complaint_id: int
    predicted_location: str
    predicted_lat: float
    predicted_lon: float
    probability: float
    risk_level: Literal["High", "Medium", "Low"]


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
