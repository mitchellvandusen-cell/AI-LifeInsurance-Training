"""
ObjectionEngine: Determines WHEN and WHAT objection the AI client should raise.
Objections are NEVER random. They are strict conditional outputs of the state machine.

Three types:
- Smokescreen: Surface-level deflection masking the true root cause.
  Almost always traces to MONEY, TIME, or DECISION_MAKER.
- True Objection: Genuine concern that must be isolated and resolved.
- Condition: External circumstance outside both parties' control. Cannot be overcome.

Isolation Protocol (putting the objection on an island):
  1. TRUTH TEST — Is the stated objection the actual concern, or a smokescreen
     masking something deeper? The spouse objection might really be about money.
     A timing objection might really be about not trusting the agent.
  2. SINGULARITY TEST — Is this the ONLY barrier? No other hidden concerns?
  3. COMMITMENT TEST — If this single issue were resolved right now, would the
     client move forward immediately? No hesitation, no new objections?
  All three must be confirmed for true isolation. Only then can the agent work
  on solving that one isolated objection. If solved properly, the deal closes.
"""

from __future__ import annotations

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
# Delay tactics trace to MONEY — the client is hesitating about the financial commitment.
# Deferral to others traces to DECISION_MAKER — the client lacks autonomous authority.
# Lack of urgency traces to TIME — no consequence was established for inaction.

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
    """A single conditional objection trigger with behavioral context."""

    def __init__(
        self,
        category: ObjectionCategory,
        objection_type: ObjectionType,
        root_cause: ObjectionRootCause,
        condition_fn,
        behavioral_intent: str,
        emotional_context: str,
        priority: int = 50,
    ):
        self.category = category
        self.objection_type = objection_type
        self.root_cause = root_cause
        self.condition_fn = condition_fn
        self.behavioral_intent = behavioral_intent
        self.emotional_context = emotional_context
        self.priority = priority

    def evaluate(self, sm: StateManager) -> bool:
        return self.condition_fn(sm)


# ── Condition categories (never trainable) ─────────────────────
# Conditions are external circumstances that neither party controls.
# They are NOT objections and CANNOT be overcome through sales technique.
# The system never triggers these as training scenarios.

CONDITION_CATEGORIES = {
    "terminal_illness": "Client has a terminal medical diagnosis that disqualifies coverage.",
    "bankruptcy": "Client is in active bankruptcy proceedings with no disposable income.",
    "no_income": "Client has no income source and cannot sustain premium payments.",
    "foreign_national": "Client does not meet citizenship or residency requirements.",
    "age_limit": "Client exceeds the maximum insurable age for available products.",
}


def _build_rules() -> list[ObjectionRule]:
    """Build the complete objection ruleset with behavioral intents."""
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
            behavioral_intent=(
                "Resist sharing banking information. This request was not "
                "contextualized in advance and feels sudden and invasive. "
                "Express protective instinct over financial details when no "
                "prior explanation was given for why this information is needed "
                "at this stage of the conversation."
            ),
            emotional_context="guarded, caught off guard, protective of financial privacy",
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
            behavioral_intent=(
                "Refuse to provide social security number. This sensitive "
                "identifier was requested without prior explanation. Express "
                "concern about identity security and question why this level "
                "of personal information is needed from someone on the phone."
            ),
            emotional_context="alarmed, suspicious, defensive about identity information",
            priority=90,
        ),
        # ── Delay / Think About It ──────────────────────────────
        # ROOT CAUSE: The client wants to delay the financial commitment.
        # No urgency was created, so there is no cost to waiting.
        ObjectionRule(
            category=ObjectionCategory.THINK_ABOUT_IT,
            objection_type=ObjectionType.SMOKESCREEN,
            root_cause=ObjectionRootCause.MONEY,
            condition_fn=lambda sm: (
                not sm.check_flag("consequence_established")
                and sm.state.current_phase == ConversationPhase.PRESENTATION
            ),
            behavioral_intent=(
                "Stall the decision by requesting time to consider. The surface "
                "behavior is asking for delay, but the root cause is unresolved "
                "financial discomfort. No consequence for inaction was established, "
                "so there is no perceived cost to waiting. Express desire to pause "
                "and reflect rather than commit now."
            ),
            emotional_context="hesitant, noncommittal, seeking an exit without confrontation",
            priority=80,
        ),
        # ── Spouse / Third Party Deferral ─────────────────────
        # ROOT CAUSE: DECISION_MAKER. Deferring authority to another person.
        # The real question is whether the client would act independently.
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
            behavioral_intent=(
                "Defer the decision to a spouse or family member. Express that "
                "this type of financial decision requires input from the other "
                "person. The underlying dynamic is using the third party as a "
                "shield against making an autonomous commitment. The client "
                "filled out the form themselves and sees the value, but is "
                "uncomfortable being the sole decision-maker."
            ),
            emotional_context="deflecting, seeking external validation, uncomfortable deciding alone",
            priority=75,
        ),
        # ── Budget / Affordability ──────────────────────────────
        ObjectionRule(
            category=ObjectionCategory.BUDGET,
            objection_type=ObjectionType.TRUE_OBJECTION,
            root_cause=ObjectionRootCause.MONEY,
            condition_fn=lambda sm: (
                sm.state.current_phase == ConversationPhase.PRESENTATION
                and sm.state.persona.budget_sensitivity > 60
                and sm.state.hidden.trust_score < 65
            ),
            behavioral_intent=(
                "Express concern about the cost. The pricing feels higher than "
                "expected or comfortable. This is a genuine financial concern, "
                "not a smokescreen. The client needs the agent to reframe the "
                "value relative to the consequence of not having coverage, or "
                "to find a more affordable option."
            ),
            emotional_context="worried about money, calculating, weighing cost against need",
            priority=60,
        ),
        # ── Trust / Credential Challenge ──────────────────────
        ObjectionRule(
            category=ObjectionCategory.TRUST,
            objection_type=ObjectionType.TRUE_OBJECTION,
            root_cause=ObjectionRootCause.MONEY,
            condition_fn=lambda sm: (
                sm.state.hidden.trust_score < 35
                and not sm.check_flag("credentials_shared")
            ),
            behavioral_intent=(
                "Question the agent's legitimacy and credentials. Trust has "
                "not been established sufficiently to continue sharing information "
                "or making commitments. Express skepticism about the caller's "
                "identity, licensing, or company affiliation. Past negative "
                "experiences with phone solicitations may surface."
            ),
            emotional_context="skeptical, wary, self-protective, questioning legitimacy",
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
            behavioral_intent=(
                "Push the decision to a future date. Express that this is not "
                "the right moment to start something new. Without an established "
                "consequence for inaction, there is no perceived cost to delaying "
                "indefinitely. The client feels no urgency because the agent "
                "never connected inaction to a specific negative outcome."
            ),
            emotional_context="disengaged from urgency, comfortable postponing, no fear of delay",
            priority=65,
        ),
        # ── Low Authority Frame Test ──────────────────────────
        ObjectionRule(
            category=ObjectionCategory.NEED,
            objection_type=ObjectionType.SMOKESCREEN,
            root_cause=ObjectionRootCause.TIME,
            condition_fn=lambda sm: sm.state.hidden.authority_score < 40,
            behavioral_intent=(
                "Attempt to seize conversational control from the agent. The "
                "agent has not established enough authority, so the client feels "
                "comfortable redirecting the conversation, asking personal or "
                "off-topic questions, or testing whether the agent can maintain "
                "their professional framework."
            ),
            emotional_context="assertive, testing boundaries, not taking the agent seriously",
            priority=55,
        ),
        # ── Intro Phase Resistance ────────────────────────────
        ObjectionRule(
            category=ObjectionCategory.NEED,
            objection_type=ObjectionType.SMOKESCREEN,
            root_cause=ObjectionRootCause.TIME,
            condition_fn=lambda sm: (
                sm.state.current_phase == ConversationPhase.INTRO
            ),
            behavioral_intent=(
                "Express initial resistance to the unsolicited call. The client "
                "is in the middle of their day and was interrupted. They may "
                "express fatigue with sales calls, claim existing coverage, "
                "assert bad timing, or question how their contact information "
                "was obtained. These are all surface-level deflections — the "
                "client DID fill out a form and has underlying interest."
            ),
            emotional_context="mildly annoyed, preoccupied, reflexively dismissive",
            priority=40,
        ),
        # ── Broken Flow Confusion ─────────────────────────────
        ObjectionRule(
            category=ObjectionCategory.THINK_ABOUT_IT,
            objection_type=ObjectionType.SMOKESCREEN,
            root_cause=ObjectionRootCause.MONEY,
            condition_fn=lambda sm: not sm.state.hidden.flow_integrity,
            behavioral_intent=(
                "Express confusion about the direction of the conversation. "
                "The call flow has been disrupted — topics jumped around or the "
                "agent backtracked in a way that broke the logical progression. "
                "The client has lost track of the purpose and structure of the "
                "conversation and defaults to requesting time to process."
            ),
            emotional_context="confused, frustrated, mentally disengaged, wanting to regroup",
            priority=85,
        ),
    ]


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

        # Combine behavioral intent and emotional context for the LLM
        objection_text = (
            f"{best.behavioral_intent}\n"
            f"Emotional state: {best.emotional_context}"
        )

        return sm.raise_objection(
            category=best.category,
            objection_type=best.objection_type,
            root_cause=best.root_cause,
            text=objection_text,
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

        # Isolation detection: agent probing for truth test + singularity test
        isolation_phrases = [
            "is it just", "is that the only", "besides that",
            "other than", "if we could", "is there anything else",
            "apart from", "or is there something else",
            "what else", "is that the real", "is there something deeper",
            "is there another reason", "what's really", "what's the real",
            "is there something behind", "anything else holding",
            "only thing", "nothing else",
        ]
        result["attempted_isolation"] = any(p in text_lower for p in isolation_phrases)

        # Hypothetical test: agent testing commitment through scenarios
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

        # Decision-maker probe: testing autonomous authority
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

        # Pressure detection: artificial urgency without substance
        pressure_phrases = [
            "today only", "right now", "can't wait",
            "don't miss", "lock in", "before it's too late",
            "what are you waiting for", "let's get this done",
            "let's do this", "pull the trigger",
        ]
        result["pressure_detected"] = any(p in text_lower for p in pressure_phrases)

        # Empathy detection: emotional acknowledgment
        empathy_phrases = [
            "i understand", "i hear you", "i get it",
            "that makes sense", "totally fair", "i appreciate",
            "you're right to", "it's smart to",
        ]
        result["empathy_shown"] = any(p in text_lower for p in empathy_phrases)

        # Consequence redirect: reconnecting to established stakes
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
          If the client admits they would proceed regardless, the objection is void.
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
                # Client admits they would proceed independently → LOCK IT.
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
