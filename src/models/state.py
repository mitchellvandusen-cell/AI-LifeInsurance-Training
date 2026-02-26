"""
Core state models for InsuranceGrokBot.
All hidden variables, phase flags, and session state live here.
"""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ConversationPhase(str, Enum):
    INTRO = "intro"
    RAPPORT_DISCOVERY = "rapport_discovery"
    MEDICAL_UNDERWRITING = "medical_underwriting"
    PREFRAMING = "preframing"
    PRESENTATION = "presentation"
    OBJECTION_HANDLING = "objection_handling"
    CLOSE = "close"


PHASE_ORDER = [
    ConversationPhase.INTRO,
    ConversationPhase.RAPPORT_DISCOVERY,
    ConversationPhase.MEDICAL_UNDERWRITING,
    ConversationPhase.PREFRAMING,
    ConversationPhase.PRESENTATION,
    ConversationPhase.OBJECTION_HANDLING,
    ConversationPhase.CLOSE,
]


class ObjectionType(str, Enum):
    SMOKESCREEN = "smokescreen"
    TRUE_OBJECTION = "true_objection"
    CONDITION = "condition"


class ObjectionCategory(str, Enum):
    BUDGET = "budget"
    TIMING = "timing"
    DECISION_MAKER = "decision_maker"
    PRODUCT_FIT = "product_fit"
    TRUST = "trust"
    NEED = "need"
    BANKING_INFO = "banking_info"
    SOCIAL_SECURITY = "social_security"
    SPOUSE_APPROVAL = "spouse_approval"
    THINK_ABOUT_IT = "think_about_it"


class ObjectionRecord(BaseModel):
    """Tracks a single objection through its lifecycle."""
    category: ObjectionCategory
    objection_type: ObjectionType
    text: str
    raised_at_phase: ConversationPhase
    isolated: bool = False
    isolation_confirmed: bool = False
    locked: bool = False
    resolved: bool = False
    resolution_conviction_score: float = 0.0
    raised_at_turn: int = 0


class PhaseFlags(BaseModel):
    """Boolean flags tracking whether critical actions occurred in each phase."""
    preoccupation_broken: bool = False
    rapport_established: bool = False
    goal_identified: bool = False
    why_behind_goal_identified: bool = False
    consequence_established: bool = False
    underwriting_clear: bool = False
    medication_history_complete: bool = False
    preframed_social_security: bool = False
    preframed_banking: bool = False
    preframed_next_steps: bool = False
    pricing_presented: bool = False
    coverage_aligned_to_goals: bool = False
    benefits_explained: bool = False
    day_one_coverage_mentioned: bool = False
    term_duration_explained: bool = False
    compliance_loop_established: bool = False
    credentials_shared: bool = False


class TonalitySnapshot(BaseModel):
    """Acoustic metadata for a single agent utterance."""
    upward_inflection_on_statements: bool = False
    downward_inflection_on_questions: bool = False
    downward_inflection_on_consequence: bool = False
    strategic_pause_detected: bool = False
    strategic_stutter_detected: bool = False
    whisper_on_key_phrase: bool = False
    tone_shift_detected: bool = False
    nervous_tone: bool = False
    confident_tone: bool = False
    pause_duration_seconds: float = 0.0
    speaking_rate_wpm: float = 0.0


class ScoreSnapshot(BaseModel):
    """Point-in-time capture of all scores for trend analysis."""
    turn_number: int
    timestamp: float
    trust_score: float
    authority_score: float
    sales_resistance: float
    rapport_score: float
    flow_integrity: bool
    phase: ConversationPhase


class HiddenState(BaseModel):
    """The complete hidden state machine. Drives all AI client behavior."""
    trust_score: float = Field(default=50.0, ge=0.0, le=100.0)
    authority_score: float = Field(default=50.0, ge=0.0, le=100.0)
    sales_resistance: float = Field(default=50.0, ge=0.0, le=100.0)
    rapport_score: float = Field(default=0.0, ge=0.0, le=100.0)
    flow_integrity: bool = True
    conviction_score: float = Field(default=50.0, ge=0.0, le=100.0)
    momentum: float = Field(default=0.0, ge=-100.0, le=100.0)
    engagement_level: float = Field(default=50.0, ge=0.0, le=100.0)


class SixAxisProfile(BaseModel):
    """
    Chase Hughes 6-Axis Model of Influence.
    These are the six behavioral levers the agent fills incrementally.
    Each axis is like a bottle — the agent pours into all six throughout the call.
    """
    focus: float = Field(default=50.0, ge=0.0, le=100.0)
    openness: float = Field(default=50.0, ge=0.0, le=100.0)
    connection: float = Field(default=50.0, ge=0.0, le=100.0)
    expectancy: float = Field(default=30.0, ge=0.0, le=100.0)
    compliance: float = Field(default=50.0, ge=0.0, le=100.0)
    suggestibility: float = Field(default=50.0, ge=0.0, le=100.0)


class FACEProfile(BaseModel):
    """FACE difficulty profile (project-specific persona calibration):
    Frequency of questions, Amount of resistance, Complexity of objections, Emotional volatility."""
    frequency_of_questions: float = Field(default=50.0, ge=0.0, le=100.0)
    amount_of_resistance: float = Field(default=50.0, ge=0.0, le=100.0)
    complexity_of_objections: float = Field(default=50.0, ge=0.0, le=100.0)
    emotional_volatility: float = Field(default=50.0, ge=0.0, le=100.0)


class ClientPersona(BaseModel):
    """Generated AI client with behavioral profile."""
    persona_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "John"
    age: int = 55
    occupation: str = "Retired teacher"
    marital_status: str = "Married"
    dependents: int = 2
    annual_income: int = 65000
    existing_coverage: Optional[str] = None
    health_conditions: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    tobacco_use: bool = False
    reason_for_inquiry: str = "Wants to leave something for grandkids"
    pain_points: list[str] = Field(default_factory=list)
    personality_notes: str = ""
    six_axis: SixAxisProfile = Field(default_factory=SixAxisProfile)
    face_profile: FACEProfile = Field(default_factory=FACEProfile)
    decision_maker: bool = True
    spouse_involvement: str = "none"
    budget_sensitivity: float = Field(default=50.0, ge=0.0, le=100.0)
    skepticism_level: float = Field(default=50.0, ge=0.0, le=100.0)
    urgency: float = Field(default=50.0, ge=0.0, le=100.0)
    baseline_trust: float = Field(default=50.0, ge=0.0, le=100.0)
    talkativeness: float = Field(default=50.0, ge=0.0, le=100.0)
    will_test_frame_control: bool = False
    frame_test_frequency: float = Field(default=0.2, ge=0.0, le=1.0)


class SessionState(BaseModel):
    """Complete session state. This is the single source of truth."""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    started_at: float = Field(default_factory=time.time)
    current_phase: ConversationPhase = ConversationPhase.INTRO
    turn_number: int = 0
    hidden: HiddenState = Field(default_factory=HiddenState)
    flags: PhaseFlags = Field(default_factory=PhaseFlags)
    persona: ClientPersona = Field(default_factory=ClientPersona)
    objections_raised: list[ObjectionRecord] = Field(default_factory=list)
    locked_objections: list[ObjectionCategory] = Field(default_factory=list)
    compliance_checks_attempted: int = 0
    compliance_checks_successful: int = 0
    consecutive_client_questions: int = 0
    score_history: list[ScoreSnapshot] = Field(default_factory=list)
    tonality_history: list[TonalitySnapshot] = Field(default_factory=list)
    phase_transitions: list[dict] = Field(default_factory=list)
    conversation_log: list[dict] = Field(default_factory=list)
    intro_timestamp: Optional[float] = None
    preoccupation_break_timestamp: Optional[float] = None
    elapsed_seconds: float = 0.0
