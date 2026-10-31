from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime

class StreamUrgencyLevel(str, Enum):
    CRITICAL_ALERT = "CRITICAL_ALERT"
    ELEVATED_ALERT = "ELEVATED_ALERT"
    STANDARD_LOG = "STANDARD_LOG"
    INFORMATION = "INFORMATION"
    ADAPTIVE_GUIDANCE = "ADAPTIVE_GUIDANCE"

class AgentStatus(str, Enum):
    SAFE = "SAFE"
    VIOLATION = "VIOLATION"
    ESCALATION = "ESCALATION"
    SCHEDULED_HABIT = "SCHEDULED_HABIT"
    ENVIRONMENTAL_OPTIMIZATION = "ENVIRONMENTAL_OPTIMIZATION"

class HistoryInfo(BaseModel):
    cataract_surgery: bool = False
    years_since_surgery: Optional[float] = None
    diabetic_retinopathy: bool = False
    retinal_disease: bool = False
    previous_detachment: bool = False
    age_over_50: bool = False
    # New fields for expanded agent suite
    postural_tracking_baseline: Optional[float] = None  # Minutes of tracked posture per day
    ambient_lighting_sensitivity: Optional[str] = None  # "high_sensitivity", "standard", "low_sensitivity"
    workplace_ergonomic_goals: Optional[List[str]] = Field(default_factory=list)  # User-defined wellness goals

class TelemetryFrame(BaseModel):
    user_id: str
    input_string: str
    multimodal_flags: List[str] = Field(default_factory=list)
    history: HistoryInfo = Field(default_factory=HistoryInfo)
    
    # Kinematics and orientation
    pitch: float = 0.0
    yaw: float = 0.0
    roll: float = 0.0
    
    # Gaze Compass target coordinates & scotoma mapping
    gaze_x: float = 0.0
    gaze_y: float = 0.0
    target_x: float = 0.0
    target_y: float = 0.0
    blind_x: float = 0.0
    blind_y: float = 0.0
    blind_r: float = 0.25
    
    # Reliability metrics
    confidence: float = 95.0
    
    # Ergonomic habit tracking (time duration in seconds at current posture)
    posture_hold_duration: float = 0.0
    
    # Environmental metadata (ambient light intensity 0-100%, contrast level)
    ambient_light_intensity: Optional[float] = None
    contrast_adaptation_mode: Optional[str] = None  # "high_contrast", "standard", "low_contrast"
    visual_field_clearance: float = 1.0
    perceived_size_delta: float = 0.0
    text_wavy_index: float = 0.0
    vocal_stress_score: float = 0.0
    oem_platform: Optional[str] = None
    
    # Router identification tokens
    client_id: Optional[str] = None
    user_token: Optional[str] = None
    agent_mode: Optional[str] = None  # Explicitly passed agent mode

class PostOpRecoveryGuidance(BaseModel):
    triple_pillow_triangle: bool = True
    airway_clearance: str = "Implement Triple Pillow Triangle layout to support chest alignment."
    positioning_instruction: str
    recommended_side: str
    timestamp: str

class StreamResponseData(BaseModel):
    status: str
    action_required: str
    confidence_score: float
    escalation_trigger: Optional[str] = None
    disclaimer: str = "Experimental prototype output; not validated for clinical use or patient guidance."
    reasoning: str
    timestamp: str
    post_op_recovery_guidance: Optional[PostOpRecoveryGuidance] = None
    pan_localization: Optional[float] = None
    platform_oem: Optional[str] = None  # Hardware vendor identifier
    ui_transformations: Optional[Dict[str, Any]] = None
    cognitive_reassurance_string: Optional[str] = None
    compliance_gate: Dict[str, str] = {
        "software_classification": "Experimental prototype; regulatory status not assessed.",
        "regulatory_disclaimer": "Not validated for diagnosis, treatment, triage, or patient guidance.",
        "fail_safe_status": "Not evaluated or certified.",
        "pii_anonymization_standard": "No certified standard; do not submit identifiable or health information."
    }

class OrchestratorPayload(BaseModel):
    status: str
    ui_transformations: Dict[str, Any]
    cognitive_reassurance_string: str

class AdaptivePayloadResponse(BaseModel):
    message: str
    data: StreamResponseData
    timestamp: str
