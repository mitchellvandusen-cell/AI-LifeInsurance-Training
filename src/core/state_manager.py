"""
StateManager: The brain of InsuranceGrokBot.
Owns the SessionState and provides all mutation methods.
Every score change flows through here with clamping and history tracking.
"""

from __future__ import annotations

import time

from src.models.state import (
    ConversationPhase,
    HiddenState,
    ObjectionCategory,
    ObjectionRecord,
    ObjectionType,
    PHASE_ORDER,
    PhaseFlags,
    ScoreSnapshot,
    SessionState,
    TonalitySnapshot,
)


class StateManager:
    """Manages the complete session state. Single source of truth."""

    def __init__(self, state: SessionState | None = None):
        self.state = state or SessionState()

    def _clamp(self, value: float, lo: float = 0.0, hi: float = 100.0) -> float:
        return max(lo, min(hi, value))

    def _snapshot(self) -> None:
        """Record current scores for trend analysis."""
        snap = ScoreSnapshot(
            turn_number=self.state.turn_number,
            timestamp=time.time(),
            trust_score=self.state.hidden.trust_score,
            authority_score=self.state.hidden.authority_score,
            sales_resistance=self.state.hidden.sales_resistance,
            rapport_score=self.state.hidden.rapport_score,
            flow_integrity=self.state.hidden.flow_integrity,
            phase=self.state.current_phase,
        )
        self.state.score_history.append(snap)

    # ── Score Mutations ─────────────────────────────────────────────

    def adjust_trust(self, delta: float, reason: str = "") -> None:
        old = self.state.hidden.trust_score
        self.state.hidden.trust_score = self._clamp(old + delta)
        self._recalculate_resistance()
        self._snapshot()

    def adjust_authority(self, delta: float, reason: str = "") -> None:
        old = self.state.hidden.authority_score
        self.state.hidden.authority_score = self._clamp(old + delta)
        self._recalculate_resistance()
        self._snapshot()

    def adjust_rapport(self, delta: float, reason: str = "") -> None:
        old = self.state.hidden.rapport_score
        self.state.hidden.rapport_score = self._clamp(old + delta)
        self._snapshot()

    def adjust_conviction(self, delta: float, reason: str = "") -> None:
        old = self.state.hidden.conviction_score
        self.state.hidden.conviction_score = self._clamp(old + delta)
        self._snapshot()

    def adjust_engagement(self, delta: float, reason: str = "") -> None:
        old = self.state.hidden.engagement_level
        self.state.hidden.engagement_level = self._clamp(old + delta)
        self._snapshot()

    def _recalculate_resistance(self) -> None:
        """Sales resistance is inversely tied to trust + authority."""
        trust = self.state.hidden.trust_score
        authority = self.state.hidden.authority_score
        base_resistance = 100.0 - ((trust * 0.5) + (authority * 0.5))
        # Preframe misses spike resistance
        penalty = 0.0
        if self.state.current_phase.value in ("presentation", "close"):
            flags = self.state.flags
            if not flags.preframed_banking:
                penalty += 10.0
            if not flags.preframed_social_security:
                penalty += 8.0
            if not flags.preframed_next_steps:
                penalty += 5.0
            if not flags.consequence_established:
                penalty += 15.0
        self.state.hidden.sales_resistance = self._clamp(base_resistance + penalty)

    def calculate_momentum(self) -> float:
        """Calculate score momentum from recent history. Positive = trending up."""
        history = self.state.score_history
        if len(history) < 3:
            self.state.hidden.momentum = 0.0
            return 0.0
        recent = history[-5:]
        trust_deltas = []
        auth_deltas = []
        for i in range(1, len(recent)):
            trust_deltas.append(recent[i].trust_score - recent[i - 1].trust_score)
            auth_deltas.append(
                recent[i].authority_score - recent[i - 1].authority_score
            )
        avg_trust_d = sum(trust_deltas) / len(trust_deltas)
        avg_auth_d = sum(auth_deltas) / len(auth_deltas)
        momentum = (avg_trust_d + avg_auth_d) / 2.0
        self.state.hidden.momentum = self._clamp(momentum, -100.0, 100.0)
        return self.state.hidden.momentum

    # ── Phase Management ────────────────────────────────────────────

    def advance_phase(self, to_phase: ConversationPhase) -> bool:
        """Advance to a new phase. Returns False if it's a backward skip (breaks flow)."""
        current_idx = PHASE_ORDER.index(self.state.current_phase)
        target_idx = PHASE_ORDER.index(to_phase)

        if target_idx < current_idx:
            self.state.hidden.flow_integrity = False
            self.adjust_trust(-10, "backward phase skip")
            self.adjust_authority(-10, "backward phase skip")

        self.state.phase_transitions.append(
            {
                "from": self.state.current_phase.value,
                "to": to_phase.value,
                "turn": self.state.turn_number,
                "timestamp": time.time(),
                "was_backward": target_idx < current_idx,
            }
        )
        self.state.current_phase = to_phase
        return target_idx >= current_idx

    def get_phase_index(self) -> int:
        return PHASE_ORDER.index(self.state.current_phase)

    # ── Flag Setters ────────────────────────────────────────────────

    def set_flag(self, flag_name: str, value: bool = True) -> None:
        if hasattr(self.state.flags, flag_name):
            setattr(self.state.flags, flag_name, value)

    def check_flag(self, flag_name: str) -> bool:
        return getattr(self.state.flags, flag_name, False)

    # ── Objection Tracking ──────────────────────────────────────────

    def raise_objection(
        self,
        category: ObjectionCategory,
        objection_type: ObjectionType,
        text: str,
    ) -> ObjectionRecord | None:
        """Raise an objection if the category is not locked."""
        if category in self.state.locked_objections:
            return None
        record = ObjectionRecord(
            category=category,
            objection_type=objection_type,
            text=text,
            raised_at_phase=self.state.current_phase,
            raised_at_turn=self.state.turn_number,
        )
        self.state.objections_raised.append(record)
        return record

    def isolate_objection(self, category: ObjectionCategory) -> None:
        """Mark the most recent objection in this category as isolated."""
        for obj in reversed(self.state.objections_raised):
            if obj.category == category and not obj.locked:
                obj.isolated = True
                break

    def confirm_isolation(self, category: ObjectionCategory) -> None:
        """Client confirms the isolated objection is the real issue."""
        for obj in reversed(self.state.objections_raised):
            if obj.category == category and obj.isolated:
                obj.isolation_confirmed = True
                break

    def resolve_objection(
        self, category: ObjectionCategory, conviction: float
    ) -> None:
        """Resolve and lock an objection. Conviction 0-100 rates the handle quality."""
        for obj in reversed(self.state.objections_raised):
            if obj.category == category and obj.isolation_confirmed and not obj.locked:
                obj.resolved = True
                obj.resolution_conviction_score = conviction
                obj.locked = True
                self.state.locked_objections.append(category)
                self.adjust_trust(conviction * 0.1, f"objection resolved: {category.value}")
                break

    def is_objection_locked(self, category: ObjectionCategory) -> bool:
        return category in self.state.locked_objections

    # ── Compliance Tracking ─────────────────────────────────────────

    def record_compliance_attempt(self, successful: bool) -> None:
        self.state.compliance_checks_attempted += 1
        if successful:
            self.state.compliance_checks_successful += 1
            self.adjust_authority(3, "compliance check passed")
        else:
            self.adjust_authority(-2, "compliance check failed")

    def get_compliance_ratio(self) -> float:
        if self.state.compliance_checks_attempted == 0:
            return 0.0
        return (
            self.state.compliance_checks_successful
            / self.state.compliance_checks_attempted
        )

    # ── Frame Control ───────────────────────────────────────────────

    def record_client_question(self) -> None:
        """Track consecutive client questions (agent losing frame)."""
        self.state.consecutive_client_questions += 1
        if self.state.consecutive_client_questions >= 2:
            self.adjust_authority(
                -5 * self.state.consecutive_client_questions,
                "client asking consecutive questions",
            )

    def record_agent_regained_frame(self) -> None:
        """Agent asked a redirecting question after answering client's question."""
        self.state.consecutive_client_questions = 0
        self.adjust_authority(5, "agent regained frame")

    # ── Tonality Processing ─────────────────────────────────────────

    def process_tonality(self, snapshot: TonalitySnapshot) -> None:
        """Apply tonality-based score adjustments."""
        self.state.tonality_history.append(snapshot)

        if snapshot.upward_inflection_on_statements:
            self.adjust_authority(-5, "upward inflection on statement")
            self.adjust_trust(-3, "sounds uncertain")

        if snapshot.downward_inflection_on_consequence:
            self.adjust_authority(5, "downward inflection on consequence")
            self.adjust_trust(3, "authoritative delivery")

        if snapshot.strategic_pause_detected and snapshot.pause_duration_seconds >= 2.0:
            self.adjust_trust(4, "strategic pause after heavy question")

        if snapshot.strategic_stutter_detected:
            self.adjust_trust(3, "strategic stutter - human element")

        if snapshot.whisper_on_key_phrase:
            self.adjust_authority(4, "whisper on key phrase")
            self.adjust_trust(2, "intimacy signal")

        if snapshot.nervous_tone:
            self.adjust_trust(-5, "nervous tone detected")
            self.adjust_authority(-5, "nervous tone detected")

        if snapshot.confident_tone:
            self.adjust_trust(3, "confident tone")
            self.adjust_authority(3, "confident tone")

    # ── Turn Management ─────────────────────────────────────────────

    def increment_turn(self) -> int:
        self.state.turn_number += 1
        self.state.elapsed_seconds = time.time() - self.state.started_at
        self.calculate_momentum()
        return self.state.turn_number

    def log_message(self, role: str, content: str, metadata: dict | None = None) -> None:
        self.state.conversation_log.append(
            {
                "turn": self.state.turn_number,
                "role": role,
                "content": content,
                "timestamp": time.time(),
                "phase": self.state.current_phase.value,
                "metadata": metadata or {},
            }
        )

    # ── State Export ────────────────────────────────────────────────

    def get_state_for_prompt(self) -> dict:
        """Export state variables for injection into the LLM system prompt."""
        return {
            "trust_score": round(self.state.hidden.trust_score, 1),
            "authority_score": round(self.state.hidden.authority_score, 1),
            "sales_resistance": round(self.state.hidden.sales_resistance, 1),
            "rapport_score": round(self.state.hidden.rapport_score, 1),
            "conviction_score": round(self.state.hidden.conviction_score, 1),
            "momentum": round(self.state.hidden.momentum, 1),
            "engagement_level": round(self.state.hidden.engagement_level, 1),
            "flow_integrity": self.state.hidden.flow_integrity,
            "current_phase": self.state.current_phase.value,
            "turn_number": self.state.turn_number,
            "flags": self.state.flags.model_dump(),
            "locked_objections": [o.value for o in self.state.locked_objections],
            "compliance_ratio": round(self.get_compliance_ratio(), 2),
            "consecutive_client_questions": self.state.consecutive_client_questions,
        }

    def export_full_state(self) -> dict:
        """Export full state for debugging or persistence."""
        return self.state.model_dump()
