"""
ObjectionEngine: Determines WHEN and WHAT objection the AI client should raise.
Objections are NEVER random. They are strict conditional outputs of the state machine.

Three types:
- Smokescreen: Surface-level deflection. The real issue is something else.
- True Objection: Genuine concern that must be isolated and resolved.
- Condition: Out of both parties' hands. Cannot be overcome. Never trained as objectable.
"""

from __future__ import annotations

from src.core.state_manager import StateManager
from src.models.state import (
    ConversationPhase,
    ObjectionCategory,
    ObjectionRecord,
    ObjectionType,
)


# Objection trigger rules: each is a function (StateManager) -> ObjectionRecord | None
class ObjectionRule:
    """A single conditional objection trigger."""

    def __init__(
        self,
        category: ObjectionCategory,
        objection_type: ObjectionType,
        condition_fn,
        text_options: list[str],
        priority: int = 50,
    ):
        self.category = category
        self.objection_type = objection_type
        self.condition_fn = condition_fn
        self.text_options = text_options
        self.priority = priority

    def evaluate(self, sm: StateManager) -> bool:
        return self.condition_fn(sm)


def _build_rules() -> list[ObjectionRule]:
    """Build the complete objection ruleset."""
    return [
        # ── Banking Objection ───────────────────────────────────
        ObjectionRule(
            category=ObjectionCategory.BANKING_INFO,
            objection_type=ObjectionType.TRUE_OBJECTION,
            condition_fn=lambda sm: (
                not sm.check_flag("preframed_banking")
                and sm.state.current_phase
                in (ConversationPhase.PRESENTATION, ConversationPhase.CLOSE)
            ),
            text_options=[
                "Whoa, I'm not giving you my banking info over the phone.",
                "I don't feel comfortable sharing my bank details right now.",
                "Why do you need my banking information?",
                "I'd rather mail in a payment. I don't give that out over the phone.",
            ],
            priority=90,
        ),
        # ── Social Security Objection ───────────────────────────
        ObjectionRule(
            category=ObjectionCategory.SOCIAL_SECURITY,
            objection_type=ObjectionType.TRUE_OBJECTION,
            condition_fn=lambda sm: (
                not sm.check_flag("preframed_social_security")
                and sm.state.current_phase
                in (ConversationPhase.PRESENTATION, ConversationPhase.CLOSE)
            ),
            text_options=[
                "I'm not giving out my social security number.",
                "Why would you need my social? That sounds like a scam.",
                "I don't give that out to anyone.",
            ],
            priority=90,
        ),
        # ── "Think About It" (consequence not established) ──────
        ObjectionRule(
            category=ObjectionCategory.THINK_ABOUT_IT,
            objection_type=ObjectionType.SMOKESCREEN,
            condition_fn=lambda sm: (
                not sm.check_flag("consequence_established")
                and sm.state.current_phase == ConversationPhase.PRESENTATION
            ),
            text_options=[
                "This sounds good, but I need to think about it.",
                "Let me sleep on it and get back to you.",
                "I'm not ready to make a decision right now.",
                "I want to do some more research first.",
            ],
            priority=80,
        ),
        # ── Spouse/Third Party (consequence not established) ────
        ObjectionRule(
            category=ObjectionCategory.SPOUSE_APPROVAL,
            objection_type=ObjectionType.SMOKESCREEN,
            condition_fn=lambda sm: (
                not sm.check_flag("consequence_established")
                and sm.state.current_phase
                in (ConversationPhase.PRESENTATION, ConversationPhase.CLOSE)
                and sm.state.persona.marital_status.lower() in ("married", "partnered")
            ),
            text_options=[
                "I need to talk to my wife about this first.",
                "My husband handles the finances, I'd need to check with him.",
                "Let me run this by my kids first, they help with these decisions.",
            ],
            priority=75,
        ),
        # ── Budget Objection ────────────────────────────────────
        ObjectionRule(
            category=ObjectionCategory.BUDGET,
            objection_type=ObjectionType.TRUE_OBJECTION,
            condition_fn=lambda sm: (
                sm.state.current_phase == ConversationPhase.PRESENTATION
                and sm.state.persona.budget_sensitivity > 60
                and sm.state.hidden.trust_score < 65
            ),
            text_options=[
                "That's more than I was hoping to spend.",
                "I don't know if I can afford that right now.",
                "That's a lot of money on a fixed income.",
                "Can you find something cheaper?",
            ],
            priority=60,
        ),
        # ── Trust / Credential Challenge ────────────────────────
        ObjectionRule(
            category=ObjectionCategory.TRUST,
            objection_type=ObjectionType.TRUE_OBJECTION,
            condition_fn=lambda sm: (
                sm.state.hidden.trust_score < 35
                and not sm.check_flag("credentials_shared")
            ),
            text_options=[
                "How do I know you're legitimate?",
                "What company are you with exactly?",
                "Are you even licensed in my state?",
                "I've been burned before by people selling insurance over the phone.",
            ],
            priority=70,
        ),
        # ── Low Authority Frame Test ────────────────────────────
        ObjectionRule(
            category=ObjectionCategory.NEED,
            objection_type=ObjectionType.SMOKESCREEN,
            condition_fn=lambda sm: sm.state.hidden.authority_score < 40,
            text_options=[
                "Actually, let me ask you something — how long have you been doing this?",
                "Hold on, before we go further, can I ask you a question?",
                "You know what, I was actually just thinking about something else entirely.",
                "Hey, real quick, what do you think about the market right now?",
            ],
            priority=55,
        ),
        # ── Intro Objections (always possible) ──────────────────
        ObjectionRule(
            category=ObjectionCategory.NEED,
            objection_type=ObjectionType.SMOKESCREEN,
            condition_fn=lambda sm: (
                sm.state.current_phase == ConversationPhase.INTRO
            ),
            text_options=[
                "Look, I get about ten of these calls a day.",
                "I already have life insurance, I'm all set.",
                "I'm not interested, take me off your list.",
                "How did you even get my number?",
                "I'm really busy right now, this isn't a good time.",
            ],
            priority=40,
        ),
        # ── Confused / Bad Flow ─────────────────────────────────
        ObjectionRule(
            category=ObjectionCategory.THINK_ABOUT_IT,
            objection_type=ObjectionType.SMOKESCREEN,
            condition_fn=lambda sm: not sm.state.hidden.flow_integrity,
            text_options=[
                "I'm confused, what exactly are we doing here?",
                "Wait, I thought we were talking about something else.",
                "You know what, let me think about it and I'll call you back.",
                "I'm going to need to think about this, you're losing me a bit.",
            ],
            priority=85,
        ),
    ]


# ── Conditions (never trainable as objections) ─────────────────

CONDITION_EXAMPLES = {
    "terminal_illness": "I was just diagnosed with stage 4 cancer last week.",
    "bankruptcy": "I just filed for bankruptcy, I have no money.",
    "no_income": "I lost my job and I'm homeless.",
    "foreign_national": "I'm not a US citizen or resident.",
    "age_limit": "I'm 96 years old.",
}


class ObjectionEngine:
    """Evaluates state and determines if/what objection should fire."""

    def __init__(self):
        self.rules = _build_rules()

    def evaluate(self, sm: StateManager) -> ObjectionRecord | None:
        """
        Check all rules against current state.
        Returns the highest priority triggered objection, or None.
        """
        triggered = []
        for rule in self.rules:
            if sm.is_objection_locked(rule.category):
                continue
            if rule.evaluate(sm):
                triggered.append(rule)

        if not triggered:
            return None

        # Sort by priority (highest first)
        triggered.sort(key=lambda r: r.priority, reverse=True)
        best = triggered[0]

        # Select text based on persona traits for variety
        import hashlib
        seed = hashlib.md5(
            f"{sm.state.session_id}{sm.state.turn_number}".encode()
        ).hexdigest()
        idx = int(seed, 16) % len(best.text_options)

        return sm.raise_objection(
            category=best.category,
            objection_type=best.objection_type,
            text=best.text_options[idx],
        )

    def should_accept_handle(self, sm: StateManager, handle_text: str) -> tuple[bool, float]:
        """
        Determine if the AI client should accept an objection handle.
        Returns (accept: bool, conviction_score: float).

        The handle is accepted if:
        1. The objection was properly isolated and confirmed
        2. Trust + Authority are above threshold
        3. The handle is logically sound (scored by LLM)

        conviction_score rates how convincing the handle was (0-100).
        """
        trust = sm.state.hidden.trust_score
        authority = sm.state.hidden.authority_score

        # Find the active (non-locked) objection
        active_objections = [
            o for o in sm.state.objections_raised
            if not o.locked and o.isolation_confirmed
        ]

        if not active_objections:
            return False, 0.0

        obj = active_objections[-1]

        # Conditions are NEVER solvable
        if obj.objection_type == ObjectionType.CONDITION:
            return False, 0.0

        # Base acceptance threshold
        threshold = 50.0

        # Adjust threshold based on objection type
        if obj.objection_type == ObjectionType.SMOKESCREEN:
            threshold -= 15  # Smokescreens are easier to handle
        elif obj.objection_type == ObjectionType.TRUE_OBJECTION:
            threshold += 10  # True objections need stronger handles

        # State-based adjustments
        score = (trust * 0.4 + authority * 0.4 + sm.state.hidden.rapport_score * 0.2)

        accept = score >= threshold
        conviction = min(100.0, max(0.0, score - threshold + 50))

        return accept, conviction

    def get_objection_context(self, sm: StateManager) -> dict:
        """Get context about objections for the LLM prompt."""
        active = [
            o.model_dump()
            for o in sm.state.objections_raised
            if not o.locked
        ]
        locked = [o.value for o in sm.state.locked_objections]
        return {
            "active_objections": active,
            "locked_objections": locked,
            "total_raised": len(sm.state.objections_raised),
            "total_resolved": len(sm.state.locked_objections),
        }
