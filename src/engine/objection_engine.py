"""
ObjectionEngine: Determines WHEN and WHAT objection the AI client should raise.
Objections are NEVER random. They are strict conditional outputs of the state machine.

Three types:
- Smokescreen: Surface-level deflection. The real issue is something else.
  Almost always traces to MONEY, TIME, or DECISION_MAKER.
- True Objection: Genuine concern that must be isolated and resolved.
- Condition: Out of both parties' hands. Cannot be overcome. Never trained as objectable.

Isolation means: "If this ONE thing were solved, would you move forward?"
For spouse/third-party: "If they said no, what would YOU do?"
Once the client confirms they'd proceed regardless, the objection is VOID and locked.
"""

from __future__ import annotations

import hashlib

from src.core.state_manager import StateManager
from src.models.state import (
    ConversationPhase,
    ObjectionCategory,
    ObjectionRecord,
    ObjectionRootCause,
    ObjectionType,
)


# ── Root cause mapping ──────────────────────────────────────────
# Every objection category maps to its true root cause.
# "I need to think about it" = thinking about SPENDING THE MONEY.
# "Talk to spouse" = talking to spouse about SPENDING THE MONEY.
# If the agent never established urgency (TIME), there's no reason to act now.

ROOT_CAUSE_MAP: dict[ObjectionCategory, ObjectionRootCause] = {
    ObjectionCategory.BUDGET: ObjectionRootCause.MONEY,
    ObjectionCategory.BANKING_INFO: ObjectionRootCause.MONEY,
    ObjectionCategory.THINK_ABOUT_IT: ObjectionRootCause.MONEY,
    ObjectionCategory.SPOUSE_APPROVAL: ObjectionRootCause.DECISION_MAKER,
    ObjectionCategory.DECISION_MAKER: ObjectionRootCause.DECISION_MAKER,
    ObjectionCategory.TIMING: ObjectionRootCause.TIME,
    ObjectionCategory.SOCIAL_SECURITY: ObjectionRootCause.MONEY,
    ObjectionCategory.TRUST: ObjectionRootCause.MONEY,
    ObjectionCategory.NEED: ObjectionRootCause.TIME,
    ObjectionCategory.PRODUCT_FIT: ObjectionRootCause.MONEY,
}


class ObjectionRule:
    """A single conditional objection trigger."""

    def __init__(
        self,
        category: ObjectionCategory,
        objection_type: ObjectionType,
        root_cause: ObjectionRootCause,
        condition_fn,
        text_options: list[str],
        priority: int = 50,
    ):
        self.category = category
        self.objection_type = objection_type
        self.root_cause = root_cause
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
            root_cause=ObjectionRootCause.MONEY,
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
            root_cause=ObjectionRootCause.MONEY,
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
        # ROOT CAUSE: They want to think about spending the MONEY.
        # No urgency was created so there's no reason to act NOW.
        ObjectionRule(
            category=ObjectionCategory.THINK_ABOUT_IT,
            objection_type=ObjectionType.SMOKESCREEN,
            root_cause=ObjectionRootCause.MONEY,
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
        # ── Spouse/Third Party ──────────────────────────────────
        # ROOT CAUSE: DECISION_MAKER. They're deferring authority.
        # Real question: Are YOU the person making this decision?
        # If the spouse said no — would you still do it?
        ObjectionRule(
            category=ObjectionCategory.SPOUSE_APPROVAL,
            objection_type=ObjectionType.SMOKESCREEN,
            root_cause=ObjectionRootCause.DECISION_MAKER,
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
                "I don't make these kinds of decisions without talking to my spouse.",
            ],
            priority=75,
        ),
        # ── Budget Objection ────────────────────────────────────
        ObjectionRule(
            category=ObjectionCategory.BUDGET,
            objection_type=ObjectionType.TRUE_OBJECTION,
            root_cause=ObjectionRootCause.MONEY,
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
            root_cause=ObjectionRootCause.MONEY,
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
        # ── Timing / No Urgency ─────────────────────────────────
        ObjectionRule(
            category=ObjectionCategory.TIMING,
            objection_type=ObjectionType.SMOKESCREEN,
            root_cause=ObjectionRootCause.TIME,
            condition_fn=lambda sm: (
                not sm.check_flag("consequence_established")
                and sm.state.current_phase
                in (ConversationPhase.PRESENTATION, ConversationPhase.CLOSE)
                and sm.state.hidden.sales_resistance > 60
            ),
            text_options=[
                "I'm not in any rush on this. Can I call you back next month?",
                "Now's not really the best time to be starting something new.",
                "I want to wait until after the holidays to deal with this.",
                "Let me get through this month first, then we can talk.",
            ],
            priority=65,
        ),
        # ── Low Authority Frame Test ────────────────────────────
        ObjectionRule(
            category=ObjectionCategory.NEED,
            objection_type=ObjectionType.SMOKESCREEN,
            root_cause=ObjectionRootCause.TIME,
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
            root_cause=ObjectionRootCause.TIME,
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
            root_cause=ObjectionRootCause.MONEY,
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

        triggered.sort(key=lambda r: r.priority, reverse=True)
        best = triggered[0]

        seed = hashlib.md5(
            f"{sm.state.session_id}{sm.state.turn_number}".encode()
        ).hexdigest()
        idx = int(seed, 16) % len(best.text_options)

        return sm.raise_objection(
            category=best.category,
            objection_type=best.objection_type,
            root_cause=best.root_cause,
            text=best.text_options[idx],
        )

    def analyze_agent_handle(self, sm: StateManager, agent_text: str) -> dict:
        """
        Analyze the agent's objection handle attempt.
        Detects isolation attempts, hypothetical testing, decision-maker probes.

        Returns a detailed analysis of what the agent did right/wrong.
        """
        text_lower = agent_text.lower()
        result = {
            "attempted_isolation": False,
            "hypothetical_test": False,
            "decision_maker_probe": False,
            "pressure_detected": False,
            "empathy_shown": False,
            "redirect_to_consequence": False,
            "asked_followup": False,
        }

        isolation_phrases = [
            "is it just", "is that the only", "besides that",
            "other than", "if we could", "is there anything else",
            "apart from", "or is there something else",
            "what else", "is that the real",
        ]
        result["attempted_isolation"] = any(p in text_lower for p in isolation_phrases)

        # Hypothetical test: "If we solved X" / "If she said no, what would you do?"
        hypothetical_phrases = [
            "if we could", "if that weren't", "let's say",
            "hypothetically", "imagine", "what if",
            "if she said no", "if he said no",
            "if they said no", "what would you do",
            "what do you think she", "what do you think he",
            "would you still", "would you do it anyway",
            "regardless of what", "if it were just up to you",
            "say you go to", "say she comes home",
            "say he has a bad day", "she had a really bad day",
        ]
        result["hypothetical_test"] = any(p in text_lower for p in hypothetical_phrases)

        dm_phrases = [
            "who makes", "decision maker", "your decision",
            "up to you", "you're the one", "this is your",
            "whose decision", "do you need permission",
            "do you need anyone", "anyone else",
            "what would she like", "what would he like",
            "what do you think she'd like", "what do you think he'd like",
            "what do you think she would like", "what do you think he would like",
            "think she would", "think he would",
        ]
        result["decision_maker_probe"] = any(p in text_lower for p in dm_phrases)

        pressure_phrases = [
            "today only", "right now", "can't wait",
            "don't miss", "lock in", "before it's too late",
            "what are you waiting for", "let's get this done",
            "let's do this", "pull the trigger",
        ]
        result["pressure_detected"] = any(p in text_lower for p in pressure_phrases)

        empathy_phrases = [
            "i understand", "i hear you", "i get it",
            "that makes sense", "totally fair", "i appreciate",
            "you're right to", "it's smart to",
        ]
        result["empathy_shown"] = any(p in text_lower for p in empathy_phrases)

        consequence_phrases = [
            "what happens if", "god forbid", "if something happened",
            "without coverage", "left with nothing",
            "remember you said", "you mentioned earlier",
            "the reason you", "your goal was",
        ]
        result["redirect_to_consequence"] = any(p in text_lower for p in consequence_phrases)

        result["asked_followup"] = "?" in agent_text

        return result

    def should_accept_handle(
        self, sm: StateManager, handle_analysis: dict
    ) -> tuple[bool, float, str]:
        """
        Determine if the AI client should accept an objection handle.
        Returns (accept, conviction_score, reason).

        Follows the three deal-killers:
        - MONEY: Is the budget genuinely workable? Did agent reframe value?
        - TIME: Did agent establish urgency through consequence?
        - DECISION_MAKER: Did agent confirm the client would act alone?
          If the client says "I'd do it anyway" the objection is VOID.
        """
        active = [o for o in sm.state.objections_raised if not o.locked]
        if not active:
            return False, 0.0, "no_active_objection"

        obj = active[-1]

        if obj.objection_type == ObjectionType.CONDITION:
            return False, 0.0, "condition_unresolvable"

        trust = sm.state.hidden.trust_score
        authority = sm.state.hidden.authority_score
        conviction = 0.0

        # ── Decision Maker objections (spouse/third party) ──────
        if obj.root_cause == ObjectionRootCause.DECISION_MAKER:
            if handle_analysis.get("hypothetical_test") and handle_analysis.get("decision_maker_probe"):
                # Agent tested the hypothetical AND probed decision-making.
                # "What do you think she'd like about this?"
                # "Say she had a bad day, said NO — what would you do?"
                # Client says "I'd do it anyway" → LOCK IT. Never comes back.
                conviction = 80.0
                if trust > 50:
                    conviction += 10
                return True, min(conviction, 100), "decision_maker_confirmed_via_hypothetical"
            elif handle_analysis.get("hypothetical_test"):
                conviction = 60.0
                return trust > 45, conviction, "hypothetical_tested_partial"
            elif handle_analysis.get("empathy_shown") and handle_analysis.get("asked_followup"):
                conviction = 40.0
                return trust > 55, conviction, "empathy_redirect_only"
            else:
                return False, 20.0, "no_hypothetical_test"

        # ── Money objections ────────────────────────────────────
        if obj.root_cause == ObjectionRootCause.MONEY:
            if handle_analysis.get("attempted_isolation"):
                conviction += 25.0
            if handle_analysis.get("redirect_to_consequence"):
                conviction += 25.0
            if handle_analysis.get("empathy_shown"):
                conviction += 10.0
            if handle_analysis.get("asked_followup"):
                conviction += 10.0

            conviction += (trust - 50) * 0.3
            conviction += (authority - 50) * 0.2
            conviction = max(0, min(100, conviction))

            accept = conviction >= 55 and trust > 45
            reason = "money_handle"
            if handle_analysis.get("pressure_detected") and not handle_analysis.get("empathy_shown"):
                conviction *= 0.7
                reason = "pressure_without_empathy"
            return accept, conviction, reason

        # ── Time objections ─────────────────────────────────────
        if obj.root_cause == ObjectionRootCause.TIME:
            if handle_analysis.get("redirect_to_consequence"):
                conviction += 35.0
            if handle_analysis.get("empathy_shown"):
                conviction += 10.0
            if handle_analysis.get("attempted_isolation"):
                conviction += 15.0
            if handle_analysis.get("asked_followup"):
                conviction += 10.0

            conviction += (trust - 50) * 0.2
            conviction = max(0, min(100, conviction))

            accept = conviction >= 50 and sm.check_flag("consequence_established")
            return accept, conviction, "time_handle"

        # Fallback
        score = trust * 0.4 + authority * 0.4 + sm.state.hidden.rapport_score * 0.2
        return score >= 55, max(0, min(100, score)), "generic_handle"

    def get_objection_context(self, sm: StateManager) -> dict:
        """Get context about objections for the LLM prompt."""
        active = []
        for o in sm.state.objections_raised:
            if not o.locked:
                d = o.model_dump()
                d["root_cause"] = o.root_cause.value
                active.append(d)

        locked = [o.value for o in sm.state.locked_objections]
        return {
            "active_objections": active,
            "locked_objections": locked,
            "total_raised": len(sm.state.objections_raised),
            "total_resolved": len(sm.state.locked_objections),
        }
