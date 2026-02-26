"""
ComplianceTracker: Monitors micro-agreements, compliance laddering,
and authority/frame control throughout the conversation.

Based on behavioral compliance principles:
- Small agreements lead to larger ones (foot-in-the-door)
- Breaking compliance patterns signals resistance
- Frame control = who is directing the conversation
"""

from __future__ import annotations

import re

from src.core.state_manager import StateManager
from src.models.state import ConversationPhase


# Compliance check patterns (agent asking for micro-agreements)
COMPLIANCE_PATTERNS = [
    (re.compile(r"(grab|get|have) a pen", re.IGNORECASE), "pen_ready", 1),
    (re.compile(r"does that (make sense|sound (fair|good|right))", re.IGNORECASE), "understanding_check", 1),
    (re.compile(r"(are you|you) (with me|following|still there)", re.IGNORECASE), "attention_check", 1),
    (re.compile(r"(fair enough|sound good|okay|right)\?$", re.IGNORECASE), "agreement_check", 1),
    (re.compile(r"can you (do that|grab that|pull that up)", re.IGNORECASE), "action_request", 2),
    (re.compile(r"(write|jot) (this|that) down", re.IGNORECASE), "action_request", 2),
    (re.compile(r"(go ahead and|let's|let me have you)", re.IGNORECASE), "directive", 2),
    (re.compile(r"(pull up|look at|check) your", re.IGNORECASE), "action_request", 2),
]

# Client compliance response patterns
CLIENT_COMPLIANCE_POSITIVE = [
    re.compile(r"\b(yes|yeah|yep|sure|okay|ok|absolutely|of course|right|got it|mhm|uh.huh)\b", re.IGNORECASE),
    re.compile(r"\b(makes? sense|sounds? (good|fair|right)|i (can|will)|go ahead)\b", re.IGNORECASE),
]

CLIENT_COMPLIANCE_NEGATIVE = [
    re.compile(r"\b(no|nah|not really|i don't think so|why|hold on|wait)\b", re.IGNORECASE),
    re.compile(r"\b(i'm not sure|let me think|maybe|i guess)\b", re.IGNORECASE),
]

# Frame control: agent redirecting after client question
REDIRECT_PATTERNS = [
    re.compile(r"(great question|good question|i appreciate you asking)", re.IGNORECASE),
    re.compile(r"(let me|allow me to).{0,30}(and then|but first|before that)", re.IGNORECASE),
    re.compile(r"(absolutely|sure).{0,30}(now |so |but |and ).{0,20}(tell me|what|how|let)", re.IGNORECASE),
    re.compile(r"(to answer that|here's the thing).{0,30}(but|now|so|let me)", re.IGNORECASE),
]


class ComplianceTracker:
    """Tracks compliance laddering, micro-agreements, and frame control."""

    def __init__(self):
        self.compliance_ladder: list[dict] = []
        self.frame_control_events: list[dict] = []

    def detect_compliance_attempt(self, agent_text: str) -> list[dict]:
        """Detect if the agent is making a compliance check."""
        attempts = []
        for pattern, check_type, weight in COMPLIANCE_PATTERNS:
            if pattern.search(agent_text):
                attempts.append({
                    "type": check_type,
                    "weight": weight,
                    "text_match": pattern.pattern,
                })
        return attempts

    def evaluate_client_compliance(self, client_text: str) -> tuple[bool, float]:
        """
        Determine if the client's response shows compliance.
        Returns (compliant: bool, strength: float 0-1).
        """
        positive_score = 0
        negative_score = 0

        for p in CLIENT_COMPLIANCE_POSITIVE:
            if p.search(client_text):
                positive_score += 1

        for p in CLIENT_COMPLIANCE_NEGATIVE:
            if p.search(client_text):
                negative_score += 1

        total = positive_score + negative_score
        if total == 0:
            return True, 0.5  # Neutral

        strength = positive_score / total
        return strength > 0.5, strength

    def detect_frame_redirect(self, agent_text: str) -> bool:
        """Detect if the agent successfully redirected after a client question."""
        for p in REDIRECT_PATTERNS:
            if p.search(agent_text):
                return True
        return False

    def process_agent_turn(self, agent_text: str, sm: StateManager) -> dict:
        """
        Process an agent turn for compliance and frame control.
        Returns analysis dict.
        """
        analysis = {
            "compliance_attempts": [],
            "frame_redirect": False,
            "compliance_loop_status": "not_started",
        }

        # Detect compliance attempts
        attempts = self.detect_compliance_attempt(agent_text)
        analysis["compliance_attempts"] = attempts

        # Detect frame redirect
        if sm.state.consecutive_client_questions > 0:
            has_question = "?" in agent_text
            has_redirect = self.detect_frame_redirect(agent_text)
            if has_redirect and has_question:
                analysis["frame_redirect"] = True
                sm.record_agent_regained_frame()
                self.frame_control_events.append({
                    "turn": sm.state.turn_number,
                    "type": "regained",
                })

        # Check compliance loop status
        if sm.state.compliance_checks_attempted == 0:
            analysis["compliance_loop_status"] = "not_started"
        elif sm.get_compliance_ratio() > 0.6:
            analysis["compliance_loop_status"] = "strong"
        elif sm.get_compliance_ratio() > 0.3:
            analysis["compliance_loop_status"] = "weak"
        else:
            analysis["compliance_loop_status"] = "failing"

        # Penalty: no compliance loop by Phase 3
        phase_idx = sm.get_phase_index()
        if phase_idx >= 2 and sm.state.compliance_checks_attempted == 0:
            if not sm.check_flag("compliance_loop_established"):
                sm.state.hidden.sales_resistance = min(
                    100.0, sm.state.hidden.sales_resistance + 20.0
                )

        return analysis

    def process_client_response(
        self, client_text: str, pending_compliance: bool, sm: StateManager
    ) -> dict:
        """Process a client response for compliance signals."""
        result = {
            "compliant": None,
            "strength": 0.0,
        }

        if pending_compliance:
            compliant, strength = self.evaluate_client_compliance(client_text)
            result["compliant"] = compliant
            result["strength"] = strength
            sm.record_compliance_attempt(compliant)
            self.compliance_ladder.append({
                "turn": sm.state.turn_number,
                "compliant": compliant,
                "strength": strength,
            })

        # Track if client is asking questions (losing frame)
        client_questions = re.findall(r"[^.!?]*\?", client_text)
        if client_questions:
            sm.record_client_question()

        return result

    def get_compliance_summary(self) -> dict:
        """Summary for grading."""
        if not self.compliance_ladder:
            return {
                "total_checks": 0,
                "successful": 0,
                "ratio": 0.0,
                "ladder_trend": "none",
                "frame_control_events": len(self.frame_control_events),
            }

        successful = sum(1 for c in self.compliance_ladder if c["compliant"])
        total = len(self.compliance_ladder)

        # Trend: are later checks more or less compliant?
        if len(self.compliance_ladder) >= 3:
            first_half = self.compliance_ladder[: len(self.compliance_ladder) // 2]
            second_half = self.compliance_ladder[len(self.compliance_ladder) // 2 :]
            first_rate = sum(1 for c in first_half if c["compliant"]) / len(first_half)
            second_rate = sum(1 for c in second_half if c["compliant"]) / len(second_half)
            if second_rate > first_rate + 0.1:
                trend = "improving"
            elif second_rate < first_rate - 0.1:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            "total_checks": total,
            "successful": successful,
            "ratio": round(successful / total, 2) if total else 0.0,
            "ladder_trend": trend,
            "frame_control_events": len(self.frame_control_events),
        }
