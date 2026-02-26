"""
PhaseManager: Analyzes agent utterances to detect phase transitions
and flag fulfillment. Works with the StateManager to track progression.
"""

from __future__ import annotations

import re

from src.core.state_manager import StateManager
from src.models.state import ConversationPhase


# Keyword/pattern sets for phase detection
PHASE_INDICATORS: dict[ConversationPhase, list[str]] = {
    ConversationPhase.INTRO: [
        r"how are you",
        r"my name is",
        r"i'm calling",
        r"reaching out",
        r"you (filled out|requested|submitted)",
        r"the reason for (my|the) call",
    ],
    ConversationPhase.RAPPORT_DISCOVERY: [
        r"tell me about",
        r"what('s| is) (important|going on)",
        r"why (is|do|did) (that|you|this)",
        r"what happens if",
        r"what would happen",
        r"who (depends|relies)",
        r"family",
        r"grandkids",
        r"retire",
        r"leave behind",
        r"protect",
        r"goals?",
    ],
    ConversationPhase.MEDICAL_UNDERWRITING: [
        r"medic(al|ation|ine)",
        r"health (history|condition|question)",
        r"prescri(bed|ption)",
        r"doctor",
        r"diagnosed",
        r"hospital",
        r"surgery",
        r"blood pressure",
        r"diabetes",
        r"cholesterol",
        r"tobacco",
        r"smok(e|ing)",
        r"height.{0,10}weight",
        r"last 10 years",
        r"past (5|10|ten|five) years",
    ],
    ConversationPhase.PREFRAMING: [
        r"(next|here('s| is) what).{0,30}(going to|gonna|will) happen",
        r"(need|ask).{0,20}(social|ssn|social security)",
        r"(need|ask).{0,20}(bank|routing|account)",
        r"before we (move|go|get)",
        r"i('m| am) going to (need|ask|have)",
        r"the (application|process) (requires|needs|will)",
    ],
    ConversationPhase.PRESENTATION: [
        r"\$\d+",
        r"per month",
        r"monthly",
        r"premium",
        r"coverage (amount|of)",
        r"(term|whole|universal) life",
        r"(level|graded|modified)",
        r"living benefits",
        r"day (one|1) coverage",
        r"beneficiary",
        r"death benefit",
        r"face (amount|value)",
    ],
    ConversationPhase.CLOSE: [
        r"(let('s| us)|ready to) (get|start) (you|this)",
        r"(application|apply|enroll)",
        r"(first|last) name",
        r"date of birth",
        r"(billing|payment) (date|method|info)",
        r"routing number",
        r"congratulations",
    ],
}

# Flag detection patterns
FLAG_PATTERNS: dict[str, list[str]] = {
    "goal_identified": [
        r"(want|looking|need|hope).{0,30}(coverage|insurance|protect|leave|provide)",
        r"my goal",
        r"what (i|we) want",
    ],
    "why_behind_goal_identified": [
        r"why.{0,20}(important|matter|want|need)",
        r"because.{0,30}(family|kids|wife|husband|grandkids)",
        r"reason.{0,20}(behind|for|why)",
    ],
    "consequence_established": [
        r"what (happens|would happen) if.{0,20}(don't|didn't|nothing|no coverage)",
        r"without (this|coverage|insurance|protection)",
        r"god forbid",
        r"worst case",
        r"if something (happen|were to)",
        r"left behind with nothing",
    ],
    "credentials_shared": [
        r"(licensed|certified|appointed)",
        r"(years|experience) in (the |this )?(industry|business|field)",
        r"my (license|certification|agency)",
        r"i (work|am) with",
    ],
    "preframed_banking": [
        r"(going to|gonna|will) (need|ask).{0,30}(bank|routing|account)",
        r"(reason|why).{0,20}(bank|routing|account)",
        r"(just like|similar to|same as).{0,20}(any|every|all).{0,20}(bill|payment)",
    ],
    "preframed_social_security": [
        r"(going to|gonna|will) (need|ask).{0,30}(social|ssn)",
        r"(reason|why).{0,20}(social|ssn)",
        r"(verify|confirm).{0,20}identity",
    ],
    "preframed_next_steps": [
        r"(here('s| is)|this is) (what|how).{0,20}(going to|gonna|will) (work|happen|go)",
        r"next (step|thing)",
        r"(process|from here) (is|works|looks like)",
    ],
    "compliance_loop_established": [
        r"(grab|get) a pen",
        r"does that make sense",
        r"(are you|you) with me",
        r"(sound|make sense|fair enough)\??$",
        r"can you do that",
        r"(right|ok|okay)\?$",
    ],
    "day_one_coverage_mentioned": [
        r"day (one|1) coverage",
        r"covered (immediately|right away|from day one|starting)",
        r"(no|without) waiting period",
    ],
    "term_duration_explained": [
        r"\d+ year term",
        r"(whole|permanent) life",
        r"(level|graded).{0,10}(term|period|years)",
        r"(coverage|policy) (lasts?|for) (life|\d+ years)",
    ],
}


class PhaseManager:
    """Detects phase transitions and flag fulfillment from agent text."""

    def __init__(self):
        self._compiled_phase: dict[ConversationPhase, list[re.Pattern]] = {
            phase: [re.compile(p, re.IGNORECASE) for p in patterns]
            for phase, patterns in PHASE_INDICATORS.items()
        }
        self._compiled_flags: dict[str, list[re.Pattern]] = {
            flag: [re.compile(p, re.IGNORECASE) for p in patterns]
            for flag, patterns in FLAG_PATTERNS.items()
        }

    def detect_phase(self, agent_text: str, sm: StateManager) -> ConversationPhase | None:
        """
        Detect which phase the agent's text belongs to.
        Returns the detected phase or None if no strong signal.
        """
        scores: dict[ConversationPhase, int] = {}
        for phase, patterns in self._compiled_phase.items():
            hits = sum(1 for p in patterns if p.search(agent_text))
            if hits > 0:
                scores[phase] = hits

        if not scores:
            return None

        # Return the phase with the most pattern matches
        detected = max(scores, key=scores.get)
        return detected

    def analyze_agent_turn(self, agent_text: str, sm: StateManager) -> dict:
        """
        Full analysis of an agent turn:
        1. Detect phase transition
        2. Check flag fulfillment
        3. Detect compliance attempts
        4. Return analysis summary
        """
        analysis = {
            "detected_phase": None,
            "phase_transition": False,
            "flags_triggered": [],
            "compliance_attempt": False,
            "preoccupation_break": False,
            "questions_asked": 0,
            "advancing_questions": 0,
        }

        # Phase detection
        detected = self.detect_phase(agent_text, sm)
        if detected:
            analysis["detected_phase"] = detected.value
            if detected != sm.state.current_phase:
                analysis["phase_transition"] = True

        # Flag detection
        for flag_name, patterns in self._compiled_flags.items():
            for p in patterns:
                if p.search(agent_text):
                    if not sm.check_flag(flag_name):
                        sm.set_flag(flag_name, True)
                        analysis["flags_triggered"].append(flag_name)
                    break

        # Compliance attempt detection
        compliance_patterns = self._compiled_flags.get("compliance_loop_established", [])
        for p in compliance_patterns:
            if p.search(agent_text):
                analysis["compliance_attempt"] = True
                break

        # Preoccupation break (intro phase, first 30 seconds)
        if sm.state.current_phase == ConversationPhase.INTRO:
            preoccupation_patterns = [
                re.compile(r"(the reason|why i'm calling|purpose of)", re.IGNORECASE),
                re.compile(r"you (requested|filled out|asked about|reached out)", re.IGNORECASE),
                re.compile(r"(quick|brief|just a moment)", re.IGNORECASE),
            ]
            for p in preoccupation_patterns:
                if p.search(agent_text):
                    analysis["preoccupation_break"] = True
                    sm.set_flag("preoccupation_broken", True)
                    break

        # Count questions
        questions = re.findall(r"[^.!?]*\?", agent_text)
        analysis["questions_asked"] = len(questions)

        # Determine if questions advance the sale
        advancing_patterns = [
            re.compile(r"(what|why|how|when|who).{0,30}(important|matter|need|want|goal|cover|protect)", re.IGNORECASE),
            re.compile(r"(tell me|share|walk me through|help me understand)", re.IGNORECASE),
            re.compile(r"(does that|make sense|sound fair|sound good|right)\?", re.IGNORECASE),
        ]
        for q in questions:
            for p in advancing_patterns:
                if p.search(q):
                    analysis["advancing_questions"] += 1
                    break

        return analysis

    def check_mandatory_flags_for_phase(
        self, phase: ConversationPhase, sm: StateManager
    ) -> list[str]:
        """Return list of missing mandatory flags for a given phase."""
        requirements: dict[ConversationPhase, list[str]] = {
            ConversationPhase.MEDICAL_UNDERWRITING: [
                "rapport_established",
                "goal_identified",
            ],
            ConversationPhase.PREFRAMING: [
                "underwriting_clear",
            ],
            ConversationPhase.PRESENTATION: [
                "consequence_established",
                "preframed_banking",
                "preframed_social_security",
                "preframed_next_steps",
            ],
            ConversationPhase.CLOSE: [
                "pricing_presented",
                "coverage_aligned_to_goals",
                "benefits_explained",
            ],
        }
        required = requirements.get(phase, [])
        missing = [f for f in required if not sm.check_flag(f)]
        return missing
