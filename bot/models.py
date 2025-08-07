"""
Pydantic models for Silli Bot data contracts
"""

from datetime import datetime
from typing import List, Dict, Optional, Union
from pydantic import BaseModel, Field


class FeatureSummary(BaseModel):
    """Audio feature summary for voice analysis."""
    level_dbfs: float = Field(..., description="Audio level in dBFS")
    centroid_norm: float = Field(..., description="Normalized spectral centroid")
    rolloff_norm: float = Field(..., description="Normalized spectral rolloff")
    flux_norm: float = Field(..., description="Normalized spectral flux")
    vad_fraction: float = Field(..., description="Voice activity detection fraction")
    stationarity: float = Field(..., description="Audio stationarity measure")


class PwaSessionReport(BaseModel):
    """PWA session report from the Dyad."""
    ts_start: str = Field(..., description="ISO-8601 timestamp")
    duration_s: int = Field(..., description="Session duration in seconds")
    mode: str = Field(..., description="Session mode (helper|low_power)")
    family_id: str = Field(..., description="Family identifier")
    session_id: str = Field(..., description="Session identifier")
    scales: Dict[str, int] = Field(..., description="Time scales in seconds")
    features_summary: FeatureSummary = Field(..., description="Aggregated audio features")
    score: Union[Dict[str, int], int] = Field(..., description="Score(s) and trend")
    badges: List[str] = Field(default_factory=list, description="Detected badges")
    events: List[Dict[str, Union[int, str]]] = Field(default_factory=list, description="Session events")
    pii: bool = Field(False, description="Contains personally identifiable information")
    version: str = Field("pwa_0.1", description="PWA version")


class EventRecord(BaseModel):
    """Event record for JSONL logging."""
    ts: datetime = Field(..., description="Timestamp with timezone")
    family_id: str = Field(..., description="Anonymous family identifier")
    session_id: str = Field(..., description="Session identifier")
    phase: str = Field(..., description="Session phase (adhoc, etc.)")
    actor: str = Field(..., description="Actor (parent|bot|system)")
    event: str = Field(..., description="Event type")
    labels: List[str] = Field(default_factory=list, description="Event labels")
    features: Optional[FeatureSummary] = Field(None, description="Audio features if applicable")
    score: Optional[int] = Field(None, description="Wind-Down score (0-100)")
    suggestion_id: Optional[str] = Field(None, description="Suggestion identifier")
    pii: bool = Field(False, description="Contains personally identifiable information")
    version: str = Field("bot_0.1", description="Bot version")
    context: Optional[dict] = None
    metrics: Optional[dict] = None


class SessionRecord(BaseModel):
    """Session record for CSV roll-up."""
    family_id: str
    session_id: str
    date: str
    phase: str
    start_ts: Optional[datetime] = None
    end_ts: Optional[datetime] = None
    time_to_calm_min: Optional[float] = None
    adoption_rate: Optional[float] = None
    helpfulness_1to7: Optional[int] = None
    privacy_1to7: Optional[int] = None
    notes: Optional[str] = None 